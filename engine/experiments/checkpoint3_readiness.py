"""Read-only Checkpoint 3 readiness audit for the R5 design comparator.

This module deliberately stops before build-plan binding or physical action.  It
checks the frozen comparator, current inventory authority fingerprints, the
known stock-form conflicts, and the non-executable measurement-protocol
contract.  It never creates reservations, mixer commands, receipts, inventory
writes, formula mutations, or scientific/release authority.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Mapping
from decimal import Decimal
from pathlib import Path
from typing import Any

from engine.calibration.hashing import stable_portable_file_hash
from engine.inventory_parser import (
    CurrentInventoryMaterialization,
    InventoryMaterial,
    materialize_current_inventory,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_COMPARATOR_PATH = (
    REPOSITORY_ROOT
    / "data"
    / "governance"
    / "lavande_ambre_profond_r5_design_comparator_20260923.json"
)
DEFAULT_PROTOCOL_PATH = (
    REPOSITORY_ROOT
    / "data"
    / "governance"
    / "lavande_ambre_profond_r5_cp3_readiness_protocol_20260926_v5.json"
)
DEFAULT_INVENTORY_TEXT_PATH = REPOSITORY_ROOT / "inventory.txt"


class Checkpoint3ContractError(ValueError):
    """Raised when a Checkpoint 3 artifact is structurally unusable."""


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
        raise Checkpoint3ContractError(f"{label} is unreadable: {path}") from exc
    if not isinstance(value, dict):
        raise Checkpoint3ContractError(f"{label} must be a JSON object")
    return value


def _load_protocol(path: Path) -> dict[str, Any]:
    successor = _load_object(path, "Checkpoint 3 protocol manifest")
    schema_version = successor.get("schema_version")
    if schema_version not in {
        "lavande-ambre-profond-r5-cp3-readiness-protocol-successor-v2",
        "lavande-ambre-profond-r5-cp3-readiness-protocol-successor-v3",
        "lavande-ambre-profond-r5-cp3-readiness-protocol-successor-v4",
        "lavande-ambre-profond-r5-cp3-readiness-protocol-successor-v5",
    }:
        return successor

    predecessor = _require_mapping(
        successor.get("predecessor"),
        "protocol predecessor",
    )
    predecessor_relative = str(predecessor.get("path") or "")
    predecessor_path = (REPOSITORY_ROOT / predecessor_relative).resolve()
    if not predecessor_path.is_relative_to(REPOSITORY_ROOT.resolve()):
        raise Checkpoint3ContractError("protocol predecessor escapes repository")
    if (
        not predecessor_path.is_file()
        or _file_sha256(predecessor_path) != predecessor.get("sha256")
    ):
        raise Checkpoint3ContractError("protocol predecessor hash drift")
    base = _load_protocol(predecessor_path)

    if schema_version == (
        "lavande-ambre-profond-r5-cp3-readiness-protocol-successor-v5"
    ):
        merged = dict(base)
        merged.update(
            {
                "schema_version": schema_version,
                "protocol_id": successor.get("protocol_id"),
                "recorded_date": successor.get("recorded_date"),
                "state": successor.get("state"),
                "predecessor": dict(predecessor),
                "inputs": dict(
                    _require_mapping(successor.get("inputs"), "successor inputs")
                ),
                "blocker_order": list(
                    _require_list(successor.get("blocker_order"), "blocker order")
                ),
                "authority": dict(
                    _require_mapping(successor.get("authority"), "authority")
                ),
            }
        )
        stock_review = dict(
            _require_mapping(base.get("stock_binding_review"), "stock binding review")
        )
        stock_review.update(
            dict(
                _require_mapping(
                    successor.get("stock_binding_review"),
                    "successor stock binding review",
                )
            )
        )
        merged["stock_binding_review"] = stock_review
        for field, label in (
            ("baseline_decision_contract", "baseline decision contract"),
            ("parent_search", "parent search"),
            ("revision_decision_contract", "revision decision contract"),
            ("constant_total_basis_contract", "constant total basis contract"),
            ("measurement_protocol_contract", "measurement protocol contract"),
        ):
            merged[field] = dict(
                _require_mapping(successor.get(field), label)
            )
        return merged

    base_review = dict(
        _require_mapping(base.get("stock_binding_review"), "stock binding review")
    )
    revision = _require_mapping(
        successor.get("stock_binding_revision"),
        "stock binding revision",
    )
    candidates = [
        dict(_require_mapping(item, "predecessor row candidate"))
        for item in _require_list(
            base_review.get("row_candidate_audit"),
            "predecessor row candidate audit",
        )
    ]
    overrides = {
        _integer(item.get("source_row"), "row candidate override source_row"): dict(
            item
        )
        for item in (
            _require_mapping(raw, "row candidate override")
            for raw in _require_list(
                revision.get("row_candidate_overrides"),
                "row candidate overrides",
            )
        )
    }
    observed_rows: set[int] = set()
    for index, candidate in enumerate(candidates):
        source_row = _integer(
            candidate.get("source_row"),
            f"predecessor row candidate {index} source_row",
        )
        replacement = overrides.get(source_row)
        if replacement is not None:
            candidates[index] = replacement
            observed_rows.add(source_row)
    if observed_rows != set(overrides):
        raise Checkpoint3ContractError(
            "row candidate override does not match predecessor audit"
        )

    merged = dict(base)
    merged.update(
        {
            "schema_version": successor.get("schema_version"),
            "protocol_id": successor.get("protocol_id"),
            "recorded_date": successor.get("recorded_date"),
            "state": successor.get("state"),
            "predecessor": dict(predecessor),
            "inputs": dict(
                _require_mapping(successor.get("inputs"), "successor inputs")
            ),
            "blocker_order": list(
                _require_list(successor.get("blocker_order"), "blocker order")
            ),
            "authority": dict(
                _require_mapping(successor.get("authority"), "authority")
            ),
            "stock_binding_revision": dict(revision),
        }
    )
    base_review["conflicts"] = list(
        _require_list(revision.get("conflicts"), "revised stock conflicts")
    )
    base_review["row_candidate_audit"] = candidates
    merged["stock_binding_review"] = base_review
    if "constant_total_basis_contract" in successor:
        merged["constant_total_basis_contract"] = dict(
            _require_mapping(
                successor.get("constant_total_basis_contract"),
                "constant total basis contract",
            )
        )
    return merged


def _require_mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise Checkpoint3ContractError(f"{label} must be an object")
    return value


def _require_list(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise Checkpoint3ContractError(f"{label} must be a list")
    return value


def _ordered_unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise Checkpoint3ContractError(f"{label} must be an integer")
    try:
        return int(value)
    except ValueError as exc:
        raise Checkpoint3ContractError(f"{label} must be an integer") from exc


def _stock_payload(stock: InventoryMaterial) -> dict[str, object]:
    return {
        "stock_id": stock.stock_id,
        "name": stock.name,
        "identity_name": stock.identity_name,
        "dilution_decimal": str(Decimal(str(stock.dilution)).normalize()),
        "fraction_basis": stock.fraction_basis,
        "carrier": stock.carrier,
        "physical_form": stock.physical_form,
        "execution_ready": stock.execution_ready,
        "authority": stock.authority,
        "source_ref": stock.source_ref,
    }


def _find_exact_label_stocks(
    inventory: CurrentInventoryMaterialization,
    material: str,
) -> list[InventoryMaterial]:
    target = material.strip().casefold()
    return [
        stock
        for stock in inventory.stocks
        if stock.name.strip().casefold() == target
        or stock.identity_name.strip().casefold() == target
    ]


def _evaluate_stock_conflicts(
    protocol: Mapping[str, Any],
    inventory: CurrentInventoryMaterialization,
) -> tuple[list[dict[str, object]], list[str]]:
    review = _require_mapping(
        protocol.get("stock_binding_review"),
        "stock_binding_review",
    )
    conflicts = _require_list(review.get("conflicts"), "stock binding conflicts")
    stock_by_id = {stock.stock_id: stock for stock in inventory.stocks}
    results: list[dict[str, object]] = []
    drift_blockers: list[str] = []

    for index, raw_conflict in enumerate(conflicts):
        conflict = _require_mapping(raw_conflict, f"stock conflict {index}")
        code = str(conflict.get("code") or "").strip()
        material = str(conflict.get("material") or "").strip()
        expected_stock_id = conflict.get("expected_stock_id")
        if not code or not material:
            raise Checkpoint3ContractError(
                f"stock conflict {index} needs code and material"
            )

        result: dict[str, object] = {
            "code": code,
            "source_row": conflict.get("source_row"),
            "material": material,
            "required_stock": conflict.get("required_stock"),
            "expected_stock_id": expected_stock_id,
            "binding_authority": False,
        }

        if expected_stock_id is None:
            exact_matches = _find_exact_label_stocks(inventory, material)
            result["observed_stock"] = (
                None if not exact_matches else [_stock_payload(stock) for stock in exact_matches]
            )
            result["verification_state"] = (
                "CONFIRMED_NO_EXACT_LIVE_STOCK"
                if not exact_matches
                else "DRIFT_UNEXPECTED_EXACT_STOCK"
            )
            if exact_matches:
                drift_blockers.append("HOLD_STOCK_AUTHORITY_DRIFT")
            results.append(result)
            continue

        stock = stock_by_id.get(str(expected_stock_id))
        if stock is None:
            result["observed_stock"] = None
            result["verification_state"] = "DRIFT_EXPECTED_STOCK_MISSING"
            drift_blockers.append("HOLD_STOCK_AUTHORITY_DRIFT")
            results.append(result)
            continue

        observed = _stock_payload(stock)
        expected = _require_mapping(
            conflict.get("expected_live_stock"),
            f"expected live stock for {code}",
        )
        expected_comparable: dict[str, object] = {
            "dilution_decimal": str(
                Decimal(str(expected.get("dilution_decimal"))).normalize()
            ),
            "fraction_basis": expected.get("fraction_basis"),
            "carrier": expected.get("carrier"),
            "execution_ready": expected.get("execution_ready"),
        }
        if "physical_form" in expected:
            expected_comparable["physical_form"] = expected.get("physical_form")
        observed_comparable = {
            key: observed[key] for key in expected_comparable
        }
        verified = observed_comparable == expected_comparable
        result["observed_stock"] = observed
        result["expected_density_state"] = expected.get("density_state")
        result["verification_state"] = (
            "VERIFIED_CONFLICT" if verified else "DRIFT_STOCK_FACTS_CHANGED"
        )
        if not verified:
            drift_blockers.append("HOLD_STOCK_AUTHORITY_DRIFT")
        results.append(result)

    return results, _ordered_unique(drift_blockers)


_ROW_CANDIDATE_STATES = {
    "CANDIDATE_FORM_MATCH",
    "CANDIDATE_FORM_CONFLICT",
    "CANDIDATE_BASIS_UNRESOLVED",
    "CANDIDATE_PREPARATION_REQUIRED",
    "NO_AUTHORITY_STOCK",
    "CURRENT_TEXT_ONLY_NOT_MATERIALIZED",
    "CURRENT_TEXT_SNAPSHOT_CONFLICT",
    "PRODUCT_IDENTIFIED_NO_PHYSICAL_STOCK",
    "CANDIDATE_RECEIPT_INCOMPLETE",
    "REQUIRED_STOCK_DEPLETED",
}


def _evaluate_row_candidates(
    protocol: Mapping[str, Any],
    comparator_rows: list[Any],
    inventory: CurrentInventoryMaterialization,
) -> tuple[list[dict[str, object]], dict[str, int], list[str]]:
    review = _require_mapping(
        protocol.get("stock_binding_review"),
        "stock_binding_review",
    )
    candidates = _require_list(
        review.get("row_candidate_audit"),
        "row candidate audit",
    )
    stock_by_id = {stock.stock_id: stock for stock in inventory.stocks}
    design_rows: dict[int, str] = {}
    for index, raw_row in enumerate(comparator_rows):
        row = _require_mapping(raw_row, f"comparator row {index}")
        source_row = _integer(
            row.get("source_row"),
            f"comparator row {index} source_row",
        )
        design_rows[source_row] = str(row.get("material") or "").strip()

    results: list[dict[str, object]] = []
    seen_rows: set[int] = set()
    drift = False
    for index, raw_candidate in enumerate(candidates):
        candidate = _require_mapping(raw_candidate, f"row candidate {index}")
        source_row = _integer(
            candidate.get("source_row"),
            f"row candidate {index} source_row",
        )
        material = str(candidate.get("material") or "").strip()
        state = str(candidate.get("state") or "").strip()
        if state not in _ROW_CANDIDATE_STATES:
            raise Checkpoint3ContractError(
                f"row candidate {source_row} has unsupported state {state!r}"
            )
        if source_row in seen_rows:
            raise Checkpoint3ContractError(
                f"row candidate {source_row} is duplicated"
            )
        seen_rows.add(source_row)

        expected_material = design_rows.get(source_row)
        if expected_material != material:
            drift = True

        candidate_stock_id = candidate.get("candidate_stock_id")
        observed_stock: dict[str, object] | None = None
        verification_state = "VERIFIED_NO_AUTHORITY_CANDIDATE"
        if candidate_stock_id is not None:
            stock = stock_by_id.get(str(candidate_stock_id))
            if stock is None:
                verification_state = "DRIFT_CANDIDATE_STOCK_MISSING"
                drift = True
            else:
                observed_stock = _stock_payload(stock)
                verification_state = "VERIFIED_READ_ONLY_CANDIDATE"

        results.append(
            {
                "source_row": source_row,
                "material": material,
                "candidate_stock_id": candidate_stock_id,
                "candidate_state": state,
                "evidence_ref": candidate.get("evidence_ref"),
                "observed_stock": observed_stock,
                "verification_state": verification_state,
                "binding_authority": False,
            }
        )

    if seen_rows != set(design_rows):
        drift = True
    results.sort(
        key=lambda item: _integer(item["source_row"], "result source_row")
    )
    counts = dict(
        sorted(Counter(str(item["candidate_state"]) for item in results).items())
    )
    blockers = ["HOLD_ROW_CANDIDATE_AUDIT_DRIFT"] if drift else []
    return results, counts, blockers


def evaluate_r5_checkpoint3_readiness(
    *,
    comparator_path: Path = DEFAULT_COMPARATOR_PATH,
    protocol_path: Path = DEFAULT_PROTOCOL_PATH,
    inventory_text_path: Path = DEFAULT_INVENTORY_TEXT_PATH,
    inventory: CurrentInventoryMaterialization | None = None,
) -> dict[str, object]:
    """Return the current fail-closed R5 physical-readiness report.

    The report is deterministic for the supplied immutable inputs.  Optional
    paths exist for drift tests; they do not authorize alternate artifacts.
    """

    comparator = _load_object(comparator_path, "R5 comparator manifest")
    protocol = _load_protocol(protocol_path)
    protocol_inputs = _require_mapping(protocol.get("inputs"), "protocol inputs")
    contract = _require_mapping(
        protocol.get("comparator_contract"),
        "comparator contract",
    )
    parent_search = _require_mapping(protocol.get("parent_search"), "parent search")
    baseline_decision = _require_mapping(
        protocol.get("baseline_decision_contract"),
        "baseline decision contract",
    )
    revision_decision = _require_mapping(
        protocol.get("revision_decision_contract"),
        "revision decision contract",
    )
    stock_review = _require_mapping(
        protocol.get("stock_binding_review"),
        "stock binding review",
    )
    measurement = _require_mapping(
        protocol.get("measurement_protocol_contract"),
        "measurement protocol contract",
    )
    constant_total = _require_mapping(
        protocol.get("constant_total_basis_contract", {}),
        "constant total basis contract",
    )
    authority = dict(_require_mapping(protocol.get("authority"), "authority"))
    if any(value is not False for value in authority.values()):
        raise Checkpoint3ContractError(
            "Checkpoint 3 protocol cannot grant authority"
        )

    rows = _require_list(comparator.get("rows"), "R5 comparator rows")
    actual_comparator_sha256 = _file_sha256(comparator_path)
    actual_protocol_sha256 = _file_sha256(protocol_path)
    actual_inventory_text_sha256 = _file_sha256(inventory_text_path)
    actual_rows_sha256 = _canonical_sha256(rows)
    current_inventory = inventory or materialize_current_inventory()
    stock_confirmation_path = REPOSITORY_ROOT / str(
        protocol_inputs.get("stock_confirmation_receipt") or ""
    )
    aroma_more_resolution_path = REPOSITORY_ROOT / str(
        protocol_inputs.get("aroma_more_product_resolution") or ""
    )
    baseline_decision_receipt_path = REPOSITORY_ROOT / str(
        protocol_inputs.get("baseline_decision_receipt") or ""
    )

    fingerprints = {
        "design_comparator_manifest_sha256": actual_comparator_sha256,
        "source_workbook_sha256": str(
            _require_mapping(
                comparator.get("source_artifact"),
                "source artifact",
            ).get("sha256")
        ),
        "canonical_formula_rows_sha256": actual_rows_sha256,
        "checkpoint3_protocol_manifest_sha256": actual_protocol_sha256,
        "inventory_text_sha256": actual_inventory_text_sha256,
        "inventory_source_workbook_sha256": (
            current_inventory.source_workbook_sha256
        ),
        "inventory_snapshot_sha256": current_inventory.snapshot_sha256,
        "inventory_overlay_sha256": current_inventory.overlay_sha256,
        "stock_confirmation_receipt_sha256": (
            _file_sha256(stock_confirmation_path)
            if stock_confirmation_path.is_file()
            else "MISSING"
        ),
        "aroma_more_product_resolution_sha256": (
            _file_sha256(aroma_more_resolution_path)
            if aroma_more_resolution_path.is_file()
            else "MISSING"
        ),
        "baseline_decision_receipt_sha256": (
            _file_sha256(baseline_decision_receipt_path)
            if baseline_decision_receipt_path.is_file()
            else "MISSING"
        ),
        "expected_parent_sha256": str(
            _require_mapping(
                comparator.get("parent_reference"),
                "parent reference",
            ).get("sha256")
        ),
    }

    fingerprint_expectations = {
        "design_comparator_manifest_sha256": protocol_inputs.get(
            "design_comparator_manifest_sha256"
        ),
        "source_workbook_sha256": protocol_inputs.get("source_workbook_sha256"),
        "canonical_formula_rows_sha256": protocol_inputs.get(
            "canonical_formula_rows_sha256"
        ),
        "inventory_text_sha256": protocol_inputs.get("inventory_text_sha256"),
        "inventory_source_workbook_sha256": protocol_inputs.get(
            "inventory_source_workbook_sha256"
        ),
        "inventory_snapshot_sha256": protocol_inputs.get(
            "inventory_snapshot_sha256"
        ),
        "inventory_overlay_sha256": protocol_inputs.get(
            "inventory_overlay_sha256"
        ),
        "stock_confirmation_receipt_sha256": protocol_inputs.get(
            "stock_confirmation_receipt_sha256"
        ),
        "aroma_more_product_resolution_sha256": protocol_inputs.get(
            "aroma_more_product_resolution_sha256"
        ),
        "baseline_decision_receipt_sha256": protocol_inputs.get(
            "baseline_decision_receipt_sha256"
        ),
        "expected_parent_sha256": protocol_inputs.get(
            "expected_parent_sha256"
        ),
    }
    dynamic_blockers: list[str] = []
    if any(
        fingerprints[key] != expected
        for key, expected in fingerprint_expectations.items()
    ):
        dynamic_blockers.append("HOLD_INPUT_FINGERPRINT_DRIFT")

    liquids = [row for row in rows if row.get("unit") == "µL"]
    solids = [row for row in rows if row.get("unit") == "mg"]
    liquid_total = sum(
        (Decimal(str(row.get("dose"))) for row in liquids),
        Decimal(0),
    )
    solid_total = sum(
        (Decimal(str(row.get("dose"))) for row in solids),
        Decimal(0),
    )
    quantities = {
        "row_count": len(rows),
        "liquid_row_count": len(liquids),
        "liquid_total_ul": str(liquid_total),
        "solid_row_count": len(solids),
        "solid_materials": [str(row.get("material")) for row in solids],
        "solid_total_mg": str(solid_total),
        "mass_volume_never_summed": True,
    }
    expected_quantities = {
        "row_count": contract.get("row_count"),
        "liquid_row_count": contract.get("liquid_row_count"),
        "liquid_total_ul": contract.get("liquid_total_ul"),
        "solid_row_count": contract.get("solid_row_count"),
        "solid_materials": [contract.get("solid_material")],
        "solid_total_mg": contract.get("solid_total_mg"),
        "mass_volume_never_summed": contract.get("mass_volume_never_summed"),
    }
    if quantities != expected_quantities:
        dynamic_blockers.append("HOLD_COMPARATOR_CONTRACT_DRIFT")

    parent_reference = _require_mapping(
        comparator.get("parent_reference"),
        "parent reference",
    )
    if (
        parent_reference.get("verification_state")
        != "PARENT_BYTES_NOT_AVAILABLE"
        or baseline_decision.get("state")
        != "R5_STANDALONE_BASELINE_ACCEPTED"
        or baseline_decision.get("parent_bytes_required_for_baseline") is not False
        or baseline_decision.get("parent_equivalence_state")
        != "NOT_CLAIMED_STANDALONE_BASELINE"
        or baseline_decision.get("r4_equivalence_claimed") is not False
        or baseline_decision.get("r4_improvement_claimed") is not False
        or parent_search.get("bytes_present") is not False
        or parent_search.get("reconstruction_allowed") is not False
        or parent_search.get("required_for_standalone_baseline") is not False
        or parent_search.get("equivalence_claimed") is not False
        or parent_search.get("improvement_claimed") is not False
    ):
        dynamic_blockers.append("HOLD_BASELINE_DECISION_CONTRACT_DRIFT")

    stock_conflicts, stock_drift = _evaluate_stock_conflicts(
        protocol,
        current_inventory,
    )
    dynamic_blockers.extend(stock_drift)
    row_candidates, candidate_state_counts, candidate_drift = (
        _evaluate_row_candidates(protocol, rows, current_inventory)
    )
    dynamic_blockers.extend(candidate_drift)

    blocker_order = [
        str(value)
        for value in _require_list(protocol.get("blocker_order"), "blocker order")
    ]
    blockers = _ordered_unique(dynamic_blockers + blocker_order)
    side_effects = {
        "reservation_created": False,
        "mixer_command_created": False,
        "transfer_record_created": False,
        "prepared_stock_receipt_created": False,
        "inventory_modified": False,
        "formula_modified": False,
        "physical_build_instruction_created": False,
    }

    report: dict[str, object] = {
        "schema_version": "lavande-ambre-profond-r5-cp3-readiness-report-v1",
        "status": "HOLD",
        "input_integrity_state": (
            "VERIFIED" if not dynamic_blockers else "HOLD_DRIFT_DETECTED"
        ),
        "comparator_id": comparator.get("comparator_id"),
        "design_comparator_state": "ADMITTED_DESIGN_ONLY",
        "baseline_state": baseline_decision.get("state"),
        "parent_equivalence_state": baseline_decision.get(
            "parent_equivalence_state"
        ),
        "revision_state": revision_decision.get("state"),
        "stock_binding_state": "HOLD_STOCK_BINDING",
        "constant_total_basis_state": constant_total.get(
            "state",
            "HOLD_CONSTANT_TOTAL_BASIS_UNRESOLVED",
        ),
        "constant_total_basis": dict(constant_total),
        "intensity_state": "HOLD_EXACT_CURVE_APPLICABILITY",
        "measurement_protocol_state": measurement.get("state"),
        "pleasantness_state": "NOT_ESTABLISHED",
        "physical_liking_state": "NOT_TESTED",
        "formula_action": contract.get("formula_action"),
        "fingerprints": fingerprints,
        "quantities": quantities,
        "parent": {
            "expected_sha256": parent_reference.get("sha256"),
            "bytes_present": False,
            "reconstruction_allowed": False,
            "search_state": parent_search.get("state"),
            "historical_search_state": parent_search.get(
                "historical_search_state"
            ),
            "required_for_standalone_baseline": False,
            "equivalence_claimed": False,
            "improvement_claimed": False,
        },
        "baseline_decision": dict(baseline_decision),
        "revision_decision": dict(revision_decision),
        "stock_binding_coverage": {
            "required_row_count": stock_review.get("required_row_count"),
            "build_plan_bound_row_count": stock_review.get(
                "build_plan_bound_row_count"
            ),
            "read_only_candidate_row_count": sum(
                item["candidate_stock_id"] is not None
                for item in row_candidates
            ),
            "candidate_state_counts": candidate_state_counts,
            "binding_candidates_are_execution_authority": False,
        },
        "row_candidate_audit": row_candidates,
        "stock_conflicts": stock_conflicts,
        "blockers": blockers,
        "authority": authority,
        "side_effects": side_effects,
    }
    report["report_sha256"] = _canonical_sha256(report)
    return report


__all__ = [
    "Checkpoint3ContractError",
    "DEFAULT_COMPARATOR_PATH",
    "DEFAULT_INVENTORY_TEXT_PATH",
    "DEFAULT_PROTOCOL_PATH",
    "evaluate_r5_checkpoint3_readiness",
]
