"""Authority-false missing-chemical comparison contracts over native C10/C0.

The recovered project-plan schema is qualitative ancestry.  This module does
not parse its free-text comparison into an executable instruction and does not
duplicate C10 stock, dose, feasibility, proposal, replicate, or human-review
authority.  It adds only the hash-addressed semantics needed to describe a
controlled comparison and to bind later native C0/Laboratory-Beta evidence.
"""

from __future__ import annotations

import re
from dataclasses import InitVar, dataclass, field
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, Mapping

from engine.optimization.contracts import (
    AuthorizedExperimentSet,
    CandidateRole,
    ExperimentProposal,
    GateStatus,
    MixtureCandidate,
    MixtureDomain,
    SelectionStatus,
    canonical_sha256,
    is_sha256,
)
from engine.optimization.mixture_design import assess_candidate


class MissingChemicalContractError(ValueError):
    """Raised when candidate ancestry is promoted or a comparison is ambiguous."""


class ImpactPlanState(str, Enum):
    CANDIDATE_ONLY = "CANDIDATE_ONLY"
    PROTOCOL_PROPOSED = "PROTOCOL_PROPOSED"
    PROTOCOL_LOCKED = "PROTOCOL_LOCKED"


class ImpactClassification(str, Enum):
    ESSENTIAL_UNBLOCKER = "ESSENTIAL UNBLOCKER"
    HIGH_VALUE_ARCHITECTURAL_EXPANSION = "HIGH_VALUE ARCHITECTURAL EXPANSION"
    USEFUL_SPECIALIST = "USEFUL SPECIALIST"
    EVIDENCE_GAP_NOT_INVENTORY_GAP = "EVIDENCE GAP, NOT INVENTORY GAP"
    REDUNDANT_WITH_CURRENT_STOCK = "REDUNDANT WITH CURRENT STOCK"


class CandidateInventoryStatus(str, Enum):
    OWNED = "OWNED"
    VERIFY_FIRST = "VERIFY_FIRST"
    PREPARABLE = "PREPARABLE"
    PLANNED_ACQUISITION = "PLANNED_ACQUISITION"
    MISSING = "MISSING"
    OUT_OF_STOCK = "OUT_OF_STOCK"


class SourceIntegrationState(str, Enum):
    NOT_AUTOMATICALLY_ADDED = "NOT_AUTOMATICALLY_ADDED"
    CONTROLLED_TEST_PROPOSED = "CONTROLLED_TEST_PROPOSED"
    CONTROLLED_TEST_APPROVED = "CONTROLLED_TEST_APPROVED"
    REJECTED_REDUNDANT = "REJECTED_REDUNDANT"


class ComparisonArmKind(str, Enum):
    CONTROL = "CONTROL"
    OMISSION = "OMISSION"
    ADDITION = "ADDITION"
    RATIO = "RATIO"
    REPLICATE = "REPLICATE"


class CriterionDirection(str, Enum):
    AT_LEAST = "AT_LEAST"
    AT_MOST = "AT_MOST"
    DIFFERENCE = "DIFFERENCE"
    EQUIVALENCE = "EQUIVALENCE"


class ImpactDecision(str, Enum):
    HOLD = "HOLD"
    INCONCLUSIVE = "INCONCLUSIVE"
    REJECT_REDUNDANT = "REJECT_REDUNDANT"
    SUPPORTS_FURTHER_REVIEW = "SUPPORTS_FURTHER_REVIEW"


class ObservationCellStatus(str, Enum):
    OBSERVED = "OBSERVED"
    GOVERNED_MISSING = "GOVERNED_MISSING"


_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
_BLIND_CODE_RE = re.compile(r"^[A-Z0-9]{3,12}$")


def _text(value: object, field_name: str) -> str:
    result = str(value).strip()
    if not result:
        raise MissingChemicalContractError(f"{field_name} must not be empty")
    return result


def _identifier(value: object, field_name: str) -> str:
    result = _text(value, field_name)
    if not _IDENTIFIER_RE.fullmatch(result):
        raise MissingChemicalContractError(
            f"{field_name} must contain only letters, digits, dot, colon, underscore, or dash"
        )
    return result


def _sha256(value: object, field_name: str) -> str:
    result = str(value).strip().casefold()
    if not is_sha256(result):
        raise MissingChemicalContractError(f"{field_name} must be a lowercase SHA-256 digest")
    return result


def _optional_sha256(value: str | None, field_name: str) -> str | None:
    return None if value is None else _sha256(value, field_name)


def _unique_text_tuple(values: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    result = tuple(_text(value, field_name) for value in values)
    if len(result) != len(set(result)):
        raise MissingChemicalContractError(f"{field_name} must be unique")
    return result


def _decimal_text(
    value: object,
    field_name: str,
    *,
    allow_zero: bool = True,
    allow_negative: bool = False,
) -> str:
    result = _text(value, field_name)
    try:
        number = Decimal(result)
    except InvalidOperation as exc:
        raise MissingChemicalContractError(f"{field_name} must be an exact decimal") from exc
    if not number.is_finite():
        raise MissingChemicalContractError(f"{field_name} must be finite")
    if (not allow_negative and number < 0) or (not allow_zero and number == 0):
        qualifier = "nonnegative" if allow_zero else "positive"
        raise MissingChemicalContractError(f"{field_name} must be {qualifier}")
    return result


@dataclass(frozen=True, slots=True)
class StockReceiptBinding:
    """Governance receipts for one C10 stock ID; composition stays in C10."""

    stock_id: str
    exact_stock_ref_sha256: str
    preparation_receipt_sha256: str
    lifecycle_receipt_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "stock_id", _identifier(self.stock_id, "stock_id"))
        for name in (
            "exact_stock_ref_sha256",
            "preparation_receipt_sha256",
            "lifecycle_receipt_sha256",
        ):
            object.__setattr__(self, name, _sha256(getattr(self, name), name))

    def as_dict(self) -> dict[str, str]:
        return {
            "stock_id": self.stock_id,
            "exact_stock_ref_sha256": self.exact_stock_ref_sha256,
            "preparation_receipt_sha256": self.preparation_receipt_sha256,
            "lifecycle_receipt_sha256": self.lifecycle_receipt_sha256,
        }


@dataclass(frozen=True, slots=True)
class FormulaForkRecord:
    """Read-only binding to one native LabFormulaVersionEdge export."""

    edge_sha256: str
    parent_formula_sha256: str
    child_formula_sha256: str
    relationship_kind: str

    def __post_init__(self) -> None:
        for name in (
            "edge_sha256",
            "parent_formula_sha256",
            "child_formula_sha256",
        ):
            object.__setattr__(self, name, _sha256(getattr(self, name), name))
        relationship = _text(self.relationship_kind, "relationship_kind").upper()
        if relationship not in {"STOCK_NORMALIZATION", "DESIGN_REVISION"}:
            raise MissingChemicalContractError(
                "formula fork relationship must be STOCK_NORMALIZATION or DESIGN_REVISION"
            )
        object.__setattr__(self, "relationship_kind", relationship)

    def as_dict(self) -> dict[str, str]:
        return {
            "edge_sha256": self.edge_sha256,
            "parent_formula_sha256": self.parent_formula_sha256,
            "child_formula_sha256": self.child_formula_sha256,
            "relationship_kind": self.relationship_kind,
        }


@dataclass(frozen=True, slots=True)
class FormulaForkManifest:
    """Content-addressed projection of native formula edges; never a graph store."""

    records: tuple[FormulaForkRecord, ...]

    def __post_init__(self) -> None:
        records = tuple(sorted(self.records, key=lambda item: item.edge_sha256))
        if not records or any(not isinstance(item, FormulaForkRecord) for item in records):
            raise MissingChemicalContractError(
                "formula fork manifest requires FormulaForkRecord values"
            )
        edge_hashes = tuple(item.edge_sha256 for item in records)
        if len(edge_hashes) != len(set(edge_hashes)):
            raise MissingChemicalContractError("formula fork edge hashes must be unique")
        object.__setattr__(self, "records", records)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "perfume-chem-native-formula-fork-manifest-v1",
            "records": [item.as_dict() for item in self.records],
        }

    @property
    def content_sha256(self) -> str:
        return canonical_sha256(self.as_dict())


@dataclass(frozen=True, slots=True)
class ImpactCandidateIdentityBinding:
    """Exact crosswalk from one package candidate to native C10 stock identity."""

    function_id: str
    candidate: str
    native_material_id: str
    c10_stock_ids: tuple[str, ...]
    identity_crosswalk_receipt_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "function_id", _identifier(self.function_id, "function_id"))
        object.__setattr__(self, "candidate", _text(self.candidate, "candidate"))
        object.__setattr__(
            self,
            "native_material_id",
            _identifier(self.native_material_id, "native_material_id"),
        )
        stock_ids = tuple(sorted(_identifier(item, "c10_stock_id") for item in self.c10_stock_ids))
        if not stock_ids or len(stock_ids) != len(set(stock_ids)):
            raise MissingChemicalContractError(
                "candidate identity requires unique native C10 stock IDs"
            )
        object.__setattr__(self, "c10_stock_ids", stock_ids)
        object.__setattr__(
            self,
            "identity_crosswalk_receipt_sha256",
            _sha256(
                self.identity_crosswalk_receipt_sha256,
                "identity_crosswalk_receipt_sha256",
            ),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "function_id": self.function_id,
            "candidate": self.candidate,
            "native_material_id": self.native_material_id,
            "c10_stock_ids": list(self.c10_stock_ids),
            "identity_crosswalk_receipt_sha256": (self.identity_crosswalk_receipt_sha256),
        }


@dataclass(frozen=True, slots=True)
class NativeLineageBinding:
    """Exact current native lineage required before a protocol may lock."""

    target_hypothesis_sha256: str
    accepted_target_sha256: str
    inventory_mapping_sha256: str
    build_plan_sha256: str
    parent_formula_sha256: str
    inventory_snapshot_sha256: str
    formula_edge_set_sha256: str
    stock_receipts: tuple[StockReceiptBinding, ...] = ()

    def __post_init__(self) -> None:
        for name in (
            "target_hypothesis_sha256",
            "accepted_target_sha256",
            "inventory_mapping_sha256",
            "build_plan_sha256",
            "parent_formula_sha256",
            "inventory_snapshot_sha256",
            "formula_edge_set_sha256",
        ):
            object.__setattr__(self, name, _sha256(getattr(self, name), name))
        receipts = tuple(sorted(self.stock_receipts, key=lambda item: item.stock_id))
        if any(not isinstance(item, StockReceiptBinding) for item in receipts):
            raise MissingChemicalContractError(
                "stock_receipts must contain StockReceiptBinding values"
            )
        stock_ids = tuple(item.stock_id for item in receipts)
        if len(stock_ids) != len(set(stock_ids)):
            raise MissingChemicalContractError("stock receipt IDs must be unique")
        object.__setattr__(self, "stock_receipts", receipts)

    def as_dict(self) -> dict[str, Any]:
        return {
            "target_hypothesis_sha256": self.target_hypothesis_sha256,
            "accepted_target_sha256": self.accepted_target_sha256,
            "inventory_mapping_sha256": self.inventory_mapping_sha256,
            "build_plan_sha256": self.build_plan_sha256,
            "parent_formula_sha256": self.parent_formula_sha256,
            "inventory_snapshot_sha256": self.inventory_snapshot_sha256,
            "formula_edge_set_sha256": self.formula_edge_set_sha256,
            "stock_receipts": [item.as_dict() for item in self.stock_receipts],
        }

    @property
    def content_sha256(self) -> str:
        return canonical_sha256(self.as_dict())


@dataclass(frozen=True, slots=True)
class QualitativeImpactCandidate:
    function_id: str
    candidate: str
    inventory_status: CandidateInventoryStatus
    classification: ImpactClassification
    nonredundancy: str
    loss_if_omitted: str
    overdose_or_failure_mode: str
    source_controlled_comparison_text: str
    source_integration_state: SourceIntegrationState

    def __post_init__(self) -> None:
        object.__setattr__(self, "function_id", _identifier(self.function_id, "function_id"))
        for name in (
            "candidate",
            "nonredundancy",
            "loss_if_omitted",
            "overdose_or_failure_mode",
            "source_controlled_comparison_text",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        object.__setattr__(
            self,
            "inventory_status",
            CandidateInventoryStatus(self.inventory_status),
        )
        object.__setattr__(
            self,
            "classification",
            ImpactClassification(self.classification),
        )
        object.__setattr__(
            self,
            "source_integration_state",
            SourceIntegrationState(self.source_integration_state),
        )

    def as_dict(self) -> dict[str, str]:
        return {
            "function_id": self.function_id,
            "candidate": self.candidate,
            "inventory_status": self.inventory_status.value,
            "classification": self.classification.value,
            "nonredundancy": self.nonredundancy,
            "loss_if_omitted": self.loss_if_omitted,
            "overdose_or_failure_mode": self.overdose_or_failure_mode,
            "source_controlled_comparison_text": self.source_controlled_comparison_text,
            "source_integration_state": self.source_integration_state.value,
        }


@dataclass(frozen=True, slots=True)
class MissingChemicalAssessment:
    """Qualitative package ancestry that can never mutate a formula."""

    assessment_id: str
    source_package_sha256: str
    source_payload_sha256: str
    target_formula_id: str
    lineage: NativeLineageBinding
    architecture_locked: bool
    strongly_covered_functions: tuple[str, ...]
    weakly_covered_functions: tuple[str, ...]
    genuinely_missing_functions: tuple[str, ...]
    candidates: tuple[QualitativeImpactCandidate, ...]
    package_auto_integrated_materials: tuple[str, ...] = ()
    state: ImpactPlanState = field(default=ImpactPlanState.CANDIDATE_ONLY, init=False)
    formula_authority: bool = field(default=False, init=False)
    inventory_authority: bool = field(default=False, init=False)
    purchase_authority: bool = field(default=False, init=False)
    execution_authorized: bool = field(default=False, init=False)
    scientific_authority: bool = field(default=False, init=False)
    oav_authority: bool = field(default=False, init=False)
    sensory_authority: bool = field(default=False, init=False)
    safety_authority: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "assessment_id",
            _identifier(self.assessment_id, "assessment_id"),
        )
        object.__setattr__(
            self,
            "source_package_sha256",
            _sha256(self.source_package_sha256, "source_package_sha256"),
        )
        object.__setattr__(
            self,
            "source_payload_sha256",
            _sha256(self.source_payload_sha256, "source_payload_sha256"),
        )
        object.__setattr__(
            self,
            "target_formula_id",
            _identifier(self.target_formula_id, "target_formula_id"),
        )
        if not isinstance(self.lineage, NativeLineageBinding):
            raise MissingChemicalContractError("lineage must be NativeLineageBinding")
        if self.architecture_locked is not True:
            raise MissingChemicalContractError(
                "missing-chemical assessment requires architecture_locked=true"
            )
        for name in (
            "strongly_covered_functions",
            "weakly_covered_functions",
            "genuinely_missing_functions",
        ):
            object.__setattr__(
                self,
                name,
                _unique_text_tuple(tuple(getattr(self, name)), name),
            )
        if not self.genuinely_missing_functions:
            raise MissingChemicalContractError(
                "assessment requires at least one genuinely missing function"
            )
        candidates = tuple(
            sorted(self.candidates, key=lambda item: (item.function_id, item.candidate))
        )
        if not candidates:
            raise MissingChemicalContractError("assessment requires at least one candidate")
        if any(not isinstance(item, QualitativeImpactCandidate) for item in candidates):
            raise MissingChemicalContractError(
                "candidates must contain QualitativeImpactCandidate values"
            )
        candidate_keys = tuple((item.function_id, item.candidate) for item in candidates)
        if len(candidate_keys) != len(set(candidate_keys)):
            raise MissingChemicalContractError("candidate function/name pairs must be unique")
        if tuple(self.package_auto_integrated_materials):
            raise MissingChemicalContractError(
                "package auto_integrated_materials must remain empty"
            )
        object.__setattr__(self, "candidates", candidates)
        object.__setattr__(self, "package_auto_integrated_materials", ())

    @classmethod
    def from_package_payload(
        cls,
        payload: Mapping[str, Any],
        *,
        assessment_id: str,
        source_package_sha256: str,
        expected_payload_sha256: str,
        lineage: NativeLineageBinding,
    ) -> MissingChemicalAssessment:
        """Retain package text as ancestry; never interpret it as a protocol."""

        canonical_payload_sha256 = canonical_sha256(dict(payload))
        if canonical_payload_sha256 != _sha256(
            expected_payload_sha256,
            "expected_payload_sha256",
        ):
            raise MissingChemicalContractError(
                "package payload hash does not match its canonical payload bytes"
            )
        try:
            candidates = tuple(
                QualitativeImpactCandidate(
                    function_id=item["function_id"],
                    candidate=item["candidate"],
                    inventory_status=CandidateInventoryStatus(item["inventory_status"]),
                    classification=ImpactClassification(item["classification"]),
                    nonredundancy=item["nonredundancy"],
                    loss_if_omitted=item["loss_if_omitted"],
                    overdose_or_failure_mode=item["overdose_or_failure_mode"],
                    source_controlled_comparison_text=item["controlled_comparison"],
                    source_integration_state=SourceIntegrationState(item["integration_state"]),
                )
                for item in payload["candidates"]
            )
            return cls(
                assessment_id=assessment_id,
                source_package_sha256=source_package_sha256,
                source_payload_sha256=canonical_payload_sha256,
                target_formula_id=payload["target_formula_id"],
                lineage=lineage,
                architecture_locked=payload["architecture_locked"],
                strongly_covered_functions=tuple(payload["strongly_covered_functions"]),
                weakly_covered_functions=tuple(payload["weakly_covered_functions"]),
                genuinely_missing_functions=tuple(payload["genuinely_missing_functions"]),
                candidates=candidates,
                package_auto_integrated_materials=tuple(payload["auto_integrated_materials"]),
            )
        except (KeyError, TypeError) as exc:
            raise MissingChemicalContractError(
                "package payload does not satisfy the qualitative candidate shape"
            ) from exc

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "perfume-chem-missing-chemical-assessment-v1",
            "assessment_id": self.assessment_id,
            "source_package_sha256": self.source_package_sha256,
            "source_payload_sha256": self.source_payload_sha256,
            "target_formula_id": self.target_formula_id,
            "lineage": self.lineage.as_dict(),
            "architecture_locked": self.architecture_locked,
            "strongly_covered_functions": list(self.strongly_covered_functions),
            "weakly_covered_functions": list(self.weakly_covered_functions),
            "genuinely_missing_functions": list(self.genuinely_missing_functions),
            "candidates": [item.as_dict() for item in self.candidates],
            "package_auto_integrated_materials": [],
            "state": self.state.value,
            "formula_authority": self.formula_authority,
            "inventory_authority": self.inventory_authority,
            "purchase_authority": self.purchase_authority,
            "execution_authorized": self.execution_authorized,
            "scientific_authority": self.scientific_authority,
            "oav_authority": self.oav_authority,
            "sensory_authority": self.sensory_authority,
            "safety_authority": self.safety_authority,
            "release_authority": self.release_authority,
        }

    @property
    def content_sha256(self) -> str:
        return canonical_sha256(self.as_dict())


@dataclass(frozen=True, slots=True)
class ComparisonArmBinding:
    """Comparison semantics over one already-defined C10 candidate."""

    arm_id: str
    kind: ComparisonArmKind
    c10_candidate_id: str
    c10_formula_state_sha256: str
    formula_version_sha256: str
    formula_edge_sha256: str
    formula_dose_receipt_sha256: str
    matrix_manifest_sha256: str
    application_manifest_sha256: str
    application_quantity_kind: str
    application_quantity_value_text: str
    application_quantity_unit: str
    application_quantity_basis: str
    replicate_of_arm_id: str | None = None

    def __post_init__(self) -> None:
        for name in ("arm_id", "c10_candidate_id"):
            object.__setattr__(self, name, _identifier(getattr(self, name), name))
        object.__setattr__(self, "kind", ComparisonArmKind(self.kind))
        for name in (
            "c10_formula_state_sha256",
            "formula_version_sha256",
            "formula_edge_sha256",
            "formula_dose_receipt_sha256",
            "matrix_manifest_sha256",
            "application_manifest_sha256",
        ):
            object.__setattr__(self, name, _sha256(getattr(self, name), name))
        for name in (
            "application_quantity_kind",
            "application_quantity_unit",
            "application_quantity_basis",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        object.__setattr__(
            self,
            "application_quantity_value_text",
            _decimal_text(
                self.application_quantity_value_text,
                "application_quantity_value_text",
                allow_zero=False,
            ),
        )
        replicate = (
            None
            if self.replicate_of_arm_id is None
            else _identifier(self.replicate_of_arm_id, "replicate_of_arm_id")
        )
        if self.kind is ComparisonArmKind.REPLICATE and replicate is None:
            raise MissingChemicalContractError("replicate arms require replicate_of_arm_id")
        if self.kind is not ComparisonArmKind.REPLICATE and replicate is not None:
            raise MissingChemicalContractError(
                "only replicate arms may declare replicate_of_arm_id"
            )
        if replicate == self.arm_id:
            raise MissingChemicalContractError("comparison arm cannot replicate itself")
        object.__setattr__(self, "replicate_of_arm_id", replicate)

    def as_dict(self) -> dict[str, Any]:
        return {
            "arm_id": self.arm_id,
            "kind": self.kind.value,
            "c10_candidate_id": self.c10_candidate_id,
            "c10_formula_state_sha256": self.c10_formula_state_sha256,
            "formula_version_sha256": self.formula_version_sha256,
            "formula_edge_sha256": self.formula_edge_sha256,
            "formula_dose_receipt_sha256": self.formula_dose_receipt_sha256,
            "matrix_manifest_sha256": self.matrix_manifest_sha256,
            "application_manifest_sha256": self.application_manifest_sha256,
            "application_quantity_kind": self.application_quantity_kind,
            "application_quantity_value_text": self.application_quantity_value_text,
            "application_quantity_unit": self.application_quantity_unit,
            "application_quantity_basis": self.application_quantity_basis,
            "replicate_of_arm_id": self.replicate_of_arm_id,
        }


@dataclass(frozen=True, slots=True)
class BlindedAllocation:
    allocation_id: str
    arm_id: str
    blind_code: str
    presentation_order: int
    repeat_index: int

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "allocation_id",
            _identifier(self.allocation_id, "allocation_id"),
        )
        object.__setattr__(self, "arm_id", _identifier(self.arm_id, "arm_id"))
        blind_code = _text(self.blind_code, "blind_code")
        if not _BLIND_CODE_RE.fullmatch(blind_code):
            raise MissingChemicalContractError(
                "blind_code must be 3-12 uppercase letters or digits"
            )
        if isinstance(self.presentation_order, bool) or self.presentation_order <= 0:
            raise MissingChemicalContractError("presentation_order must be positive")
        if isinstance(self.repeat_index, bool) or self.repeat_index <= 0:
            raise MissingChemicalContractError("repeat_index must be positive")
        object.__setattr__(self, "blind_code", blind_code)

    def as_dict(self) -> dict[str, Any]:
        return {
            "allocation_id": self.allocation_id,
            "arm_id": self.arm_id,
            "blind_code": self.blind_code,
            "presentation_order": self.presentation_order,
            "repeat_index": self.repeat_index,
        }


@dataclass(frozen=True, slots=True)
class ExpectedObservationCell:
    """One frozen C0 observation cell expected by the comparison plan."""

    cell_id: str
    allocation_id: str
    arm_id: str
    repeat_index: int
    timepoint_seconds: int
    endpoint_id: str
    participant_token: str
    session_token: str

    def __post_init__(self) -> None:
        for name in (
            "cell_id",
            "allocation_id",
            "arm_id",
            "endpoint_id",
            "participant_token",
            "session_token",
        ):
            object.__setattr__(self, name, _identifier(getattr(self, name), name))
        if isinstance(self.repeat_index, bool) or self.repeat_index <= 0:
            raise MissingChemicalContractError("repeat_index must be positive")
        if (
            isinstance(self.timepoint_seconds, bool)
            or not isinstance(self.timepoint_seconds, int)
            or self.timepoint_seconds < 0
        ):
            raise MissingChemicalContractError("timepoint_seconds must be a nonnegative integer")

    def as_dict(self) -> dict[str, Any]:
        return {
            "cell_id": self.cell_id,
            "allocation_id": self.allocation_id,
            "arm_id": self.arm_id,
            "repeat_index": self.repeat_index,
            "timepoint_seconds": self.timepoint_seconds,
            "endpoint_id": self.endpoint_id,
            "participant_token": self.participant_token,
            "session_token": self.session_token,
        }


@dataclass(frozen=True, slots=True)
class DecisionCriterion:
    criterion_id: str
    endpoint_id: str
    metric: str
    unit: str
    direction: CriterionDirection
    threshold_value_text: str
    equivalence_margin_text: str | None
    uncertainty_method: str
    missing_data_rule: str
    tie_rule: str

    def __post_init__(self) -> None:
        for name in ("criterion_id", "endpoint_id"):
            object.__setattr__(self, name, _identifier(getattr(self, name), name))
        for name in (
            "metric",
            "unit",
            "uncertainty_method",
            "missing_data_rule",
            "tie_rule",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        direction = CriterionDirection(self.direction)
        object.__setattr__(self, "direction", direction)
        object.__setattr__(
            self,
            "threshold_value_text",
            _decimal_text(self.threshold_value_text, "threshold_value_text"),
        )
        margin = (
            None
            if self.equivalence_margin_text is None
            else _decimal_text(
                self.equivalence_margin_text,
                "equivalence_margin_text",
                allow_zero=False,
            )
        )
        if direction is CriterionDirection.EQUIVALENCE and margin is None:
            raise MissingChemicalContractError(
                "equivalence criteria require equivalence_margin_text"
            )
        if direction is not CriterionDirection.EQUIVALENCE and margin is not None:
            raise MissingChemicalContractError(
                "only equivalence criteria may declare equivalence_margin_text"
            )
        object.__setattr__(self, "equivalence_margin_text", margin)

    def as_dict(self) -> dict[str, Any]:
        return {
            "criterion_id": self.criterion_id,
            "endpoint_id": self.endpoint_id,
            "metric": self.metric,
            "unit": self.unit,
            "direction": self.direction.value,
            "threshold_value_text": self.threshold_value_text,
            "equivalence_margin_text": self.equivalence_margin_text,
            "uncertainty_method": self.uncertainty_method,
            "missing_data_rule": self.missing_data_rule,
            "tie_rule": self.tie_rule,
        }


@dataclass(frozen=True, slots=True)
class ComparisonProtocolBindings:
    c0_protocol_sha256: str | None
    sample_manifest_sha256: str | None
    randomization_manifest_sha256: str | None
    participant_plan_sha256: str | None
    qualification_policy_sha256: str | None
    analysis_plan_sha256: str | None
    uncertainty_plan_sha256: str | None
    environment_timing_manifest_sha256: str | None

    def __post_init__(self) -> None:
        for name in (
            "c0_protocol_sha256",
            "sample_manifest_sha256",
            "randomization_manifest_sha256",
            "participant_plan_sha256",
            "qualification_policy_sha256",
            "analysis_plan_sha256",
            "uncertainty_plan_sha256",
            "environment_timing_manifest_sha256",
        ):
            object.__setattr__(
                self,
                name,
                _optional_sha256(getattr(self, name), name),
            )

    def as_dict(self) -> dict[str, str | None]:
        return {
            "c0_protocol_sha256": self.c0_protocol_sha256,
            "sample_manifest_sha256": self.sample_manifest_sha256,
            "randomization_manifest_sha256": self.randomization_manifest_sha256,
            "participant_plan_sha256": self.participant_plan_sha256,
            "qualification_policy_sha256": self.qualification_policy_sha256,
            "analysis_plan_sha256": self.analysis_plan_sha256,
            "uncertainty_plan_sha256": self.uncertainty_plan_sha256,
            "environment_timing_manifest_sha256": (self.environment_timing_manifest_sha256),
        }

    def missing_binding_ids(self) -> tuple[str, ...]:
        return tuple(name for name, value in self.as_dict().items() if value is None)


@dataclass(frozen=True, slots=True)
class MissingChemicalComparisonProtocol:
    """Thin comparison wrapper; all composition feasibility is recomputed by C10."""

    protocol_id: str
    version: int
    state: ImpactPlanState
    assessment: InitVar[MissingChemicalAssessment]
    current_lineage: InitVar[NativeLineageBinding]
    domain: InitVar[MixtureDomain]
    candidates: InitVar[tuple[MixtureCandidate, ...]]
    proposal: InitVar[ExperimentProposal]
    formula_fork_manifest: InitVar[FormulaForkManifest]
    selected_impact_candidate: ImpactCandidateIdentityBinding
    arms: tuple[ComparisonArmBinding, ...]
    required_arm_kinds: tuple[ComparisonArmKind, ...]
    allocations: tuple[BlindedAllocation, ...]
    repeat_count: int
    timepoints_seconds: tuple[int, ...]
    criteria: tuple[DecisionCriterion, ...]
    bindings: ComparisonProtocolBindings
    assessment_sha256: str = field(init=False)
    native_lineage_sha256: str = field(init=False)
    c10_domain_sha256: str = field(init=False)
    c10_proposal_sha256: str = field(init=False)
    formula_fork_manifest_sha256: str = field(init=False)
    execution_authorized: bool = field(default=False, init=False)
    formula_authority: bool = field(default=False, init=False)
    inventory_authority: bool = field(default=False, init=False)
    purchase_authority: bool = field(default=False, init=False)
    scientific_authority: bool = field(default=False, init=False)
    oav_authority: bool = field(default=False, init=False)
    sensory_authority: bool = field(default=False, init=False)
    safety_authority: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)

    def __post_init__(
        self,
        assessment: MissingChemicalAssessment,
        current_lineage: NativeLineageBinding,
        domain: MixtureDomain,
        candidates: tuple[MixtureCandidate, ...],
        proposal: ExperimentProposal,
        formula_fork_manifest: FormulaForkManifest,
    ) -> None:
        object.__setattr__(
            self,
            "protocol_id",
            _identifier(self.protocol_id, "protocol_id"),
        )
        if isinstance(self.version, bool) or not isinstance(self.version, int):
            raise MissingChemicalContractError("version must be a positive integer")
        if self.version <= 0:
            raise MissingChemicalContractError("version must be a positive integer")
        state = ImpactPlanState(self.state)
        if state is ImpactPlanState.CANDIDATE_ONLY:
            raise MissingChemicalContractError(
                "candidate-only state belongs to MissingChemicalAssessment"
            )
        object.__setattr__(self, "state", state)
        if not isinstance(assessment, MissingChemicalAssessment):
            raise MissingChemicalContractError("assessment must be MissingChemicalAssessment")
        if not isinstance(current_lineage, NativeLineageBinding):
            raise MissingChemicalContractError("current_lineage must be NativeLineageBinding")
        if assessment.lineage.content_sha256 != current_lineage.content_sha256:
            raise MissingChemicalContractError("native lineage is stale or mismatched")
        if not isinstance(self.selected_impact_candidate, ImpactCandidateIdentityBinding):
            raise MissingChemicalContractError(
                "selected_impact_candidate must be ImpactCandidateIdentityBinding"
            )
        selected_package_key = (
            self.selected_impact_candidate.function_id,
            self.selected_impact_candidate.candidate,
        )
        package_keys = {(item.function_id, item.candidate) for item in assessment.candidates}
        if selected_package_key not in package_keys:
            raise MissingChemicalContractError(
                "selected impact candidate is not present in the bound assessment"
            )
        if not isinstance(domain, MixtureDomain):
            raise MissingChemicalContractError("domain must be native C10 MixtureDomain")
        if not isinstance(proposal, ExperimentProposal):
            raise MissingChemicalContractError("proposal must be native C10 ExperimentProposal")
        if proposal.status is not SelectionStatus.PROPOSED or proposal.execution_authorized:
            raise MissingChemicalContractError(
                "comparison requires a non-executable C10 PROPOSED proposal"
            )
        if proposal.blocker_codes or proposal.domain_sha256 != domain.content_sha256:
            raise MissingChemicalContractError(
                "C10 proposal is blocked or bound to a different domain"
            )
        if not isinstance(formula_fork_manifest, FormulaForkManifest):
            raise MissingChemicalContractError("formula_fork_manifest must be FormulaForkManifest")
        if formula_fork_manifest.content_sha256 != current_lineage.formula_edge_set_sha256:
            raise MissingChemicalContractError(
                "native formula fork manifest is stale or mismatched"
            )
        stock_by_id = {item.stock_id: item for item in domain.stocks}
        missing_identity_stocks = set(self.selected_impact_candidate.c10_stock_ids).difference(
            stock_by_id
        )
        if missing_identity_stocks:
            raise MissingChemicalContractError(
                "identity crosswalk references unknown C10 stock IDs: "
                + ", ".join(sorted(missing_identity_stocks))
            )
        if any(
            stock_by_id[stock_id].material_id != self.selected_impact_candidate.native_material_id
            for stock_id in self.selected_impact_candidate.c10_stock_ids
        ):
            raise MissingChemicalContractError(
                "identity crosswalk C10 stocks do not resolve to the bound native material"
            )
        candidate_values = tuple(candidates)
        if any(not isinstance(item, MixtureCandidate) for item in candidate_values):
            raise MissingChemicalContractError(
                "candidates must contain native C10 MixtureCandidate values"
            )
        candidate_by_id = {item.candidate_id: item for item in candidate_values}
        if len(candidate_by_id) != len(candidate_values):
            raise MissingChemicalContractError("C10 candidate IDs must be unique")

        arms = tuple(sorted(self.arms, key=lambda item: item.arm_id))
        if any(not isinstance(item, ComparisonArmBinding) for item in arms):
            raise MissingChemicalContractError("arms must contain ComparisonArmBinding values")
        arm_by_id = {item.arm_id: item for item in arms}
        if len(arm_by_id) != len(arms):
            raise MissingChemicalContractError("comparison arm IDs must be unique")
        selected_ids = set(proposal.selected_candidate_ids)
        stock_receipts = {item.stock_id for item in current_lineage.stock_receipts}
        identity_stock_ids = set(self.selected_impact_candidate.c10_stock_ids)
        formula_edges = {item.edge_sha256: item for item in formula_fork_manifest.records}
        formula_hash_by_arm: dict[str, str] = {}
        bound_intervention_seen = False
        for arm in arms:
            candidate = candidate_by_id.get(arm.c10_candidate_id)
            if candidate is None:
                raise MissingChemicalContractError(
                    f"arm {arm.arm_id} references an unknown C10 candidate"
                )
            if candidate.candidate_id not in selected_ids:
                raise MissingChemicalContractError(
                    f"arm {arm.arm_id} candidate is not selected by the C10 proposal"
                )
            assessment_result = assess_candidate(domain, candidate)
            if not assessment_result.feasible:
                codes = ",".join(item.code for item in assessment_result.violations)
                raise MissingChemicalContractError(
                    f"arm {arm.arm_id} C10 candidate is infeasible: {codes}"
                )
            if assessment_result.formula_state_sha256 != arm.c10_formula_state_sha256:
                raise MissingChemicalContractError(
                    f"arm {arm.arm_id} formula-state hash is stale or mismatched"
                )
            formula_hash_by_arm[arm.arm_id] = assessment_result.formula_state_sha256
            missing_stocks = {dose.stock_id for dose in candidate.doses}.difference(stock_receipts)
            if missing_stocks:
                raise MissingChemicalContractError(
                    f"arm {arm.arm_id} lacks stock/preparation receipts for "
                    + ", ".join(sorted(missing_stocks))
                )
            candidate_stock_ids = {dose.stock_id for dose in candidate.doses}
            has_bound_identity = bool(candidate_stock_ids.intersection(identity_stock_ids))
            if arm.kind in {ComparisonArmKind.ADDITION, ComparisonArmKind.RATIO}:
                if not has_bound_identity:
                    raise MissingChemicalContractError(
                        f"arm {arm.arm_id} does not contain the assessed native material"
                    )
                bound_intervention_seen = True
            elif arm.kind is ComparisonArmKind.OMISSION and has_bound_identity:
                raise MissingChemicalContractError(
                    f"omission arm {arm.arm_id} still contains the assessed native material"
                )
            fork = formula_edges.get(arm.formula_edge_sha256)
            if (
                fork is None
                or fork.child_formula_sha256 != arm.formula_version_sha256
                or fork.parent_formula_sha256 != current_lineage.parent_formula_sha256
            ):
                raise MissingChemicalContractError(
                    f"arm {arm.arm_id} is not a member of the bound native formula fork"
                )
            if arm.kind is ComparisonArmKind.CONTROL:
                if candidate.role is not CandidateRole.CONTROL:
                    raise MissingChemicalContractError(
                        "CONTROL arms must reference a native C10 CONTROL candidate"
                    )
            elif arm.kind is ComparisonArmKind.REPLICATE:
                if candidate.role is not CandidateRole.REPLICATE:
                    raise MissingChemicalContractError(
                        "REPLICATE arms must reference a native C10 REPLICATE candidate"
                    )
            elif candidate.role in {CandidateRole.CONTROL, CandidateRole.REPLICATE}:
                raise MissingChemicalContractError(
                    f"{arm.kind.value} arm cannot reuse a C10 control/replicate role"
                )
        if not bound_intervention_seen:
            raise MissingChemicalContractError(
                "comparison has no addition/ratio arm for the assessed native material"
            )

        for arm in arms:
            if arm.kind is not ComparisonArmKind.REPLICATE:
                continue
            target_arm = arm_by_id.get(arm.replicate_of_arm_id or "")
            candidate = candidate_by_id[arm.c10_candidate_id]
            if target_arm is None or candidate.replicate_of != target_arm.c10_candidate_id:
                raise MissingChemicalContractError(
                    f"replicate arm {arm.arm_id} does not match its C10 replicate target"
                )
            if formula_hash_by_arm[arm.arm_id] != formula_hash_by_arm[target_arm.arm_id]:
                raise MissingChemicalContractError(
                    f"replicate arm {arm.arm_id} composition differs from its target"
                )

        required = tuple(sorted(set(self.required_arm_kinds), key=lambda item: item.value))
        if any(not isinstance(item, ComparisonArmKind) for item in required):
            raise MissingChemicalContractError(
                "required_arm_kinds must contain ComparisonArmKind values"
            )
        allocations = tuple(sorted(self.allocations, key=lambda item: item.presentation_order))
        if any(not isinstance(item, BlindedAllocation) for item in allocations):
            raise MissingChemicalContractError("allocations must contain BlindedAllocation values")
        allocation_ids = tuple(item.allocation_id for item in allocations)
        blind_codes = tuple(item.blind_code for item in allocations)
        orders = tuple(item.presentation_order for item in allocations)
        if len(allocation_ids) != len(set(allocation_ids)):
            raise MissingChemicalContractError("allocation IDs must be unique")
        if len(blind_codes) != len(set(blind_codes)):
            raise MissingChemicalContractError("blind codes must be unique")
        if isinstance(self.repeat_count, bool) or self.repeat_count < 1:
            raise MissingChemicalContractError("repeat_count must be a positive integer")
        timepoints = tuple(self.timepoints_seconds)
        if any(
            isinstance(item, bool) or not isinstance(item, int) or item < 0 for item in timepoints
        ):
            raise MissingChemicalContractError(
                "timepoints_seconds must contain nonnegative integers"
            )
        if tuple(sorted(set(timepoints))) != timepoints:
            raise MissingChemicalContractError("timepoints_seconds must be unique and increasing")
        criteria = tuple(sorted(self.criteria, key=lambda item: item.criterion_id))
        if any(not isinstance(item, DecisionCriterion) for item in criteria):
            raise MissingChemicalContractError("criteria must contain DecisionCriterion values")
        criterion_ids = tuple(item.criterion_id for item in criteria)
        if len(criterion_ids) != len(set(criterion_ids)):
            raise MissingChemicalContractError("criterion IDs must be unique")
        if not isinstance(self.bindings, ComparisonProtocolBindings):
            raise MissingChemicalContractError("bindings must be ComparisonProtocolBindings")

        object.__setattr__(self, "arms", arms)
        object.__setattr__(self, "required_arm_kinds", required)
        object.__setattr__(self, "allocations", allocations)
        object.__setattr__(self, "timepoints_seconds", timepoints)
        object.__setattr__(self, "criteria", criteria)
        object.__setattr__(self, "assessment_sha256", assessment.content_sha256)
        object.__setattr__(
            self,
            "native_lineage_sha256",
            current_lineage.content_sha256,
        )
        object.__setattr__(self, "c10_domain_sha256", domain.content_sha256)
        object.__setattr__(self, "c10_proposal_sha256", proposal.content_sha256)
        object.__setattr__(
            self,
            "formula_fork_manifest_sha256",
            formula_fork_manifest.content_sha256,
        )

        if state is ImpactPlanState.PROTOCOL_LOCKED:
            lock_errors = self._lock_errors(arm_by_id, orders)
            if lock_errors:
                raise MissingChemicalContractError(
                    "protocol cannot lock: " + "; ".join(lock_errors)
                )

    def _lock_errors(
        self,
        arm_by_id: Mapping[str, ComparisonArmBinding],
        presentation_orders: tuple[int, ...],
    ) -> tuple[str, ...]:
        errors: list[str] = []
        kinds = {item.kind for item in self.arms}
        if ComparisonArmKind.CONTROL not in kinds:
            errors.append("a CONTROL arm is required")
        if ComparisonArmKind.REPLICATE not in kinds:
            errors.append("a REPLICATE arm is required")
        if not kinds.intersection(
            {
                ComparisonArmKind.OMISSION,
                ComparisonArmKind.ADDITION,
                ComparisonArmKind.RATIO,
            }
        ):
            errors.append("at least one OMISSION, ADDITION, or RATIO arm is required")
        missing_kinds = set(self.required_arm_kinds).difference(kinds)
        if missing_kinds:
            errors.append(
                "required arm kinds are missing: "
                + ", ".join(sorted(item.value for item in missing_kinds))
            )
        if len({item.matrix_manifest_sha256 for item in self.arms}) != 1:
            errors.append("all arms must use one matched matrix manifest")
        application_shapes = {
            (
                item.application_quantity_kind,
                item.application_quantity_value_text,
                item.application_quantity_unit,
                item.application_quantity_basis,
            )
            for item in self.arms
        }
        if len(application_shapes) != 1:
            errors.append("all arms must use one matched application quantity and basis")
        if self.repeat_count < 2:
            errors.append("repeat_count must permit repeatability assessment")
        if not self.timepoints_seconds:
            errors.append("timepoints_seconds are empty")
        if not self.criteria:
            errors.append("decision criteria are empty")
        errors.extend(f"binding {item} is missing" for item in self.bindings.missing_binding_ids())
        expected_orders = tuple(range(1, len(self.allocations) + 1))
        if presentation_orders != expected_orders:
            errors.append("presentation_order must be contiguous and explicit")
        allocations_by_arm: dict[str, set[int]] = {arm_id: set() for arm_id in arm_by_id}
        for allocation in self.allocations:
            if allocation.arm_id not in arm_by_id:
                errors.append(f"allocation {allocation.allocation_id} has unknown arm")
                continue
            allocations_by_arm[allocation.arm_id].add(allocation.repeat_index)
        expected_repeats = set(range(1, self.repeat_count + 1))
        for arm_id, repeats in allocations_by_arm.items():
            if repeats != expected_repeats:
                errors.append(f"arm {arm_id} does not have every required repeat")
        return tuple(errors)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "perfume-chem-missing-chemical-comparison-protocol-v1",
            "protocol_id": self.protocol_id,
            "version": self.version,
            "state": self.state.value,
            "assessment_sha256": self.assessment_sha256,
            "native_lineage_sha256": self.native_lineage_sha256,
            "c10_domain_sha256": self.c10_domain_sha256,
            "c10_proposal_sha256": self.c10_proposal_sha256,
            "formula_fork_manifest_sha256": self.formula_fork_manifest_sha256,
            "selected_impact_candidate": self.selected_impact_candidate.as_dict(),
            "arms": [item.as_dict() for item in self.arms],
            "required_arm_kinds": [item.value for item in self.required_arm_kinds],
            "allocations": [item.as_dict() for item in self.allocations],
            "repeat_count": self.repeat_count,
            "timepoints_seconds": list(self.timepoints_seconds),
            "criteria": [item.as_dict() for item in self.criteria],
            "bindings": self.bindings.as_dict(),
            "execution_authorized": self.execution_authorized,
            "formula_authority": self.formula_authority,
            "inventory_authority": self.inventory_authority,
            "purchase_authority": self.purchase_authority,
            "scientific_authority": self.scientific_authority,
            "oav_authority": self.oav_authority,
            "sensory_authority": self.sensory_authority,
            "safety_authority": self.safety_authority,
            "release_authority": self.release_authority,
        }

    @property
    def content_sha256(self) -> str:
        return canonical_sha256(self.as_dict())


@dataclass(frozen=True, slots=True)
class ExpectedObservationManifest:
    """Frozen expected C0 cells; no observed result may redefine the denominator."""

    protocol: InitVar[MissingChemicalComparisonProtocol]
    cells: tuple[ExpectedObservationCell, ...]
    protocol_sha256: str = field(init=False)

    def __post_init__(self, protocol: MissingChemicalComparisonProtocol) -> None:
        if protocol.state is not ImpactPlanState.PROTOCOL_LOCKED:
            raise MissingChemicalContractError(
                "expected observation cells require a locked protocol"
            )
        cells = tuple(sorted(self.cells, key=lambda item: item.cell_id))
        if not cells or any(not isinstance(item, ExpectedObservationCell) for item in cells):
            raise MissingChemicalContractError(
                "expected observation manifest requires ExpectedObservationCell values"
            )
        cell_ids = tuple(item.cell_id for item in cells)
        if len(cell_ids) != len(set(cell_ids)):
            raise MissingChemicalContractError("expected observation cell IDs must be unique")
        cell_keys = tuple(
            (
                item.allocation_id,
                item.timepoint_seconds,
                item.endpoint_id,
                item.participant_token,
                item.session_token,
            )
            for item in cells
        )
        if len(cell_keys) != len(set(cell_keys)):
            raise MissingChemicalContractError(
                "expected observation cells must have unique allocation/time/endpoint/participant/session keys"
            )
        allocations = {item.allocation_id: item for item in protocol.allocations}
        endpoints = {item.endpoint_id for item in protocol.criteria}
        timepoints = set(protocol.timepoints_seconds)
        observed_grid: set[tuple[str, int, str]] = set()
        for cell in cells:
            allocation = allocations.get(cell.allocation_id)
            if allocation is None:
                raise MissingChemicalContractError(
                    f"expected cell {cell.cell_id} references an unknown allocation"
                )
            if cell.arm_id != allocation.arm_id or cell.repeat_index != allocation.repeat_index:
                raise MissingChemicalContractError(
                    f"expected cell {cell.cell_id} does not match its frozen allocation"
                )
            if cell.timepoint_seconds not in timepoints or cell.endpoint_id not in endpoints:
                raise MissingChemicalContractError(
                    f"expected cell {cell.cell_id} is outside the locked endpoint/time grid"
                )
            observed_grid.add((cell.allocation_id, cell.timepoint_seconds, cell.endpoint_id))
        required_grid = {
            (allocation.allocation_id, timepoint, endpoint)
            for allocation in protocol.allocations
            for timepoint in protocol.timepoints_seconds
            for endpoint in endpoints
        }
        if observed_grid != required_grid:
            raise MissingChemicalContractError(
                "expected observation manifest does not cover every allocation/timepoint/endpoint cell"
            )
        object.__setattr__(self, "cells", cells)
        object.__setattr__(self, "protocol_sha256", protocol.content_sha256)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "perfume-chem-expected-observation-manifest-v1",
            "protocol_sha256": self.protocol_sha256,
            "cells": [item.as_dict() for item in self.cells],
        }

    @property
    def content_sha256(self) -> str:
        return canonical_sha256(self.as_dict())


@dataclass(frozen=True, slots=True)
class ProtocolProjectionAuthorization:
    """Separate local authorization to project JSON, never to create samples."""

    status: GateStatus
    protocol_sha256: str
    c10_authorized_set_sha256: str
    existing_bottle_manifest_sha256: str
    physical_review_evidence_sha256: str
    reviewer_role: str
    scope: str = field(default="LAB_PROTOCOL_PROJECTION_ONLY", init=False)
    execution_authorized: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "status", GateStatus(self.status))
        for name in (
            "protocol_sha256",
            "c10_authorized_set_sha256",
            "existing_bottle_manifest_sha256",
            "physical_review_evidence_sha256",
        ):
            object.__setattr__(self, name, _sha256(getattr(self, name), name))
        object.__setattr__(
            self,
            "reviewer_role",
            _text(self.reviewer_role, "reviewer_role"),
        )


def project_lab_experiment_protocol_json(
    protocol: MissingChemicalComparisonProtocol,
    c10_authorized_set: AuthorizedExperimentSet,
    authorization: ProtocolProjectionAuthorization,
) -> dict[str, Any]:
    """Project deterministic protocol JSON without writing Lab rows or bottles."""

    if protocol.state is not ImpactPlanState.PROTOCOL_LOCKED:
        raise MissingChemicalContractError("only a locked protocol may be projected")
    if not isinstance(c10_authorized_set, AuthorizedExperimentSet):
        raise MissingChemicalContractError(
            "c10_authorized_set must be native AuthorizedExperimentSet"
        )
    if c10_authorized_set.proposal_sha256 != protocol.c10_proposal_sha256:
        raise MissingChemicalContractError("C10 authorized set is bound to a different proposal")
    arm_candidates = {item.c10_candidate_id for item in protocol.arms}
    if not arm_candidates.issubset(set(c10_authorized_set.selected_candidate_ids)):
        raise MissingChemicalContractError("C10 authorized set does not cover every comparison arm")
    authorized_hash = canonical_sha256(c10_authorized_set)
    if authorization.status is not GateStatus.PASS:
        raise MissingChemicalContractError("protocol projection authorization must PASS")
    if authorization.protocol_sha256 != protocol.content_sha256:
        raise MissingChemicalContractError(
            "projection authorization is bound to a different protocol"
        )
    if authorization.c10_authorized_set_sha256 != authorized_hash:
        raise MissingChemicalContractError(
            "projection authorization is bound to a different C10 authorized set"
        )
    return {
        **protocol.as_dict(),
        "projection": {
            "scope": authorization.scope,
            "c10_authorized_set_sha256": authorized_hash,
            "existing_bottle_manifest_sha256": (authorization.existing_bottle_manifest_sha256),
            "physical_review_evidence_sha256": (authorization.physical_review_evidence_sha256),
            "reviewer_role": authorization.reviewer_role,
            "requires_existing_bottle_ids": True,
            "lab_rows_written": False,
            "samples_created": False,
            "execution_authorized": False,
        },
    }


@dataclass(frozen=True, slots=True)
class QualificationReceiptBinding:
    receipt_sha256: str
    c0_protocol_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "receipt_sha256",
            _sha256(self.receipt_sha256, "receipt_sha256"),
        )
        object.__setattr__(
            self,
            "c0_protocol_sha256",
            _sha256(self.c0_protocol_sha256, "c0_protocol_sha256"),
        )

    def as_dict(self) -> dict[str, str]:
        return {
            "receipt_sha256": self.receipt_sha256,
            "c0_protocol_sha256": self.c0_protocol_sha256,
        }


@dataclass(frozen=True, slots=True)
class ObservationReceiptBinding:
    record_sha256: str
    status: ObservationCellStatus
    application_record_sha256: str
    qualification_receipt_sha256: str
    c0_protocol_sha256: str
    expected_cell_id: str
    allocation_id: str
    arm_id: str
    repeat_index: int
    timepoint_seconds: int
    endpoint_id: str
    participant_token: str
    session_token: str
    missing_reason: str | None = None

    def __post_init__(self) -> None:
        for name in (
            "record_sha256",
            "application_record_sha256",
            "qualification_receipt_sha256",
            "c0_protocol_sha256",
        ):
            object.__setattr__(self, name, _sha256(getattr(self, name), name))
        for name in (
            "expected_cell_id",
            "allocation_id",
            "arm_id",
            "endpoint_id",
            "participant_token",
            "session_token",
        ):
            object.__setattr__(self, name, _identifier(getattr(self, name), name))
        if isinstance(self.repeat_index, bool) or self.repeat_index <= 0:
            raise MissingChemicalContractError("repeat_index must be positive")
        if (
            isinstance(self.timepoint_seconds, bool)
            or not isinstance(self.timepoint_seconds, int)
            or self.timepoint_seconds < 0
        ):
            raise MissingChemicalContractError("timepoint_seconds must be a nonnegative integer")
        status = ObservationCellStatus(self.status)
        missing = (
            None if self.missing_reason is None else _text(self.missing_reason, "missing_reason")
        )
        if status is ObservationCellStatus.OBSERVED and missing is not None:
            raise MissingChemicalContractError("observed cells cannot declare a missing_reason")
        if status is ObservationCellStatus.GOVERNED_MISSING and missing is None:
            raise MissingChemicalContractError("governed missing cells require a missing_reason")
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "missing_reason", missing)

    def as_dict(self) -> dict[str, Any]:
        return {
            "record_sha256": self.record_sha256,
            "status": self.status.value,
            "application_record_sha256": self.application_record_sha256,
            "qualification_receipt_sha256": self.qualification_receipt_sha256,
            "c0_protocol_sha256": self.c0_protocol_sha256,
            "expected_cell_id": self.expected_cell_id,
            "allocation_id": self.allocation_id,
            "arm_id": self.arm_id,
            "repeat_index": self.repeat_index,
            "timepoint_seconds": self.timepoint_seconds,
            "endpoint_id": self.endpoint_id,
            "participant_token": self.participant_token,
            "session_token": self.session_token,
            "missing_reason": self.missing_reason,
        }


@dataclass(frozen=True, slots=True)
class ComparisonEvidenceBundle:
    protocol: InitVar[MissingChemicalComparisonProtocol]
    expected_manifest: InitVar[ExpectedObservationManifest]
    qualifications: tuple[QualificationReceiptBinding, ...]
    observations: tuple[ObservationReceiptBinding, ...]
    analysis_result_sha256: str
    uncertainty_receipt_sha256: str
    protocol_sha256: str = field(init=False)
    expected_observation_manifest_sha256: str = field(init=False)
    observed_cell_count: int = field(init=False)
    governed_missing_count: int = field(init=False)

    def __post_init__(
        self,
        protocol: MissingChemicalComparisonProtocol,
        expected_manifest: ExpectedObservationManifest,
    ) -> None:
        if protocol.state is not ImpactPlanState.PROTOCOL_LOCKED:
            raise MissingChemicalContractError(
                "observations cannot bind before the protocol is locked"
            )
        c0_protocol = protocol.bindings.c0_protocol_sha256
        if c0_protocol is None:
            raise MissingChemicalContractError("locked protocol lacks a C0 protocol hash")
        if not isinstance(expected_manifest, ExpectedObservationManifest):
            raise MissingChemicalContractError(
                "expected_manifest must be ExpectedObservationManifest"
            )
        if expected_manifest.protocol_sha256 != protocol.content_sha256:
            raise MissingChemicalContractError(
                "expected observation manifest is bound to a different protocol"
            )
        qualifications = tuple(sorted(self.qualifications, key=lambda item: item.receipt_sha256))
        observations = tuple(sorted(self.observations, key=lambda item: item.expected_cell_id))
        if not qualifications or not observations:
            raise MissingChemicalContractError(
                "decision evidence requires qualification and observation receipts"
            )
        qualification_ids = {item.receipt_sha256 for item in qualifications}
        if len(qualification_ids) != len(qualifications):
            raise MissingChemicalContractError("qualification receipts must be unique")
        expected_by_id = {item.cell_id: item for item in expected_manifest.cells}
        observed_cell_ids = tuple(item.expected_cell_id for item in observations)
        if len(observed_cell_ids) != len(set(observed_cell_ids)):
            raise MissingChemicalContractError(
                "observation receipts must bind unique expected cells"
            )
        if set(observed_cell_ids) != set(expected_by_id):
            raise MissingChemicalContractError(
                "observation receipts must cover every frozen expected cell exactly once"
            )
        for qualification in qualifications:
            if qualification.c0_protocol_sha256 != c0_protocol:
                raise MissingChemicalContractError(
                    "qualification receipt is bound to a different C0 protocol"
                )
        for observation in observations:
            if observation.c0_protocol_sha256 != c0_protocol:
                raise MissingChemicalContractError(
                    "observation is bound to a different C0 protocol"
                )
            if observation.qualification_receipt_sha256 not in qualification_ids:
                raise MissingChemicalContractError("observation lacks its qualification receipt")
            expected = expected_by_id[observation.expected_cell_id]
            if (
                observation.allocation_id != expected.allocation_id
                or observation.arm_id != expected.arm_id
                or observation.repeat_index != expected.repeat_index
                or observation.timepoint_seconds != expected.timepoint_seconds
                or observation.endpoint_id != expected.endpoint_id
                or observation.participant_token != expected.participant_token
                or observation.session_token != expected.session_token
            ):
                raise MissingChemicalContractError(
                    f"observation {observation.expected_cell_id} does not match its frozen expected cell"
                )
        object.__setattr__(self, "qualifications", qualifications)
        object.__setattr__(self, "observations", observations)
        object.__setattr__(
            self,
            "analysis_result_sha256",
            _sha256(self.analysis_result_sha256, "analysis_result_sha256"),
        )
        object.__setattr__(
            self,
            "uncertainty_receipt_sha256",
            _sha256(self.uncertainty_receipt_sha256, "uncertainty_receipt_sha256"),
        )
        object.__setattr__(self, "protocol_sha256", protocol.content_sha256)
        object.__setattr__(
            self,
            "expected_observation_manifest_sha256",
            expected_manifest.content_sha256,
        )
        observed_count = sum(item.status is ObservationCellStatus.OBSERVED for item in observations)
        object.__setattr__(self, "observed_cell_count", observed_count)
        object.__setattr__(
            self,
            "governed_missing_count",
            len(observations) - observed_count,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "protocol_sha256": self.protocol_sha256,
            "expected_observation_manifest_sha256": (self.expected_observation_manifest_sha256),
            "qualifications": [item.as_dict() for item in self.qualifications],
            "observations": [item.as_dict() for item in self.observations],
            "observed_cell_count": self.observed_cell_count,
            "governed_missing_count": self.governed_missing_count,
            "analysis_result_sha256": self.analysis_result_sha256,
            "uncertainty_receipt_sha256": self.uncertainty_receipt_sha256,
        }

    @property
    def content_sha256(self) -> str:
        return canonical_sha256(self.as_dict())


@dataclass(frozen=True, slots=True)
class CriterionOutcome:
    criterion_id: str
    estimate_value_text: str | None
    standard_uncertainty_text: str | None
    unit: str
    tie: bool
    missing_reason: str | None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "criterion_id",
            _identifier(self.criterion_id, "criterion_id"),
        )
        object.__setattr__(self, "unit", _text(self.unit, "unit"))
        estimate = (
            None
            if self.estimate_value_text is None
            else _decimal_text(
                self.estimate_value_text,
                "estimate_value_text",
                allow_negative=True,
            )
        )
        uncertainty = (
            None
            if self.standard_uncertainty_text is None
            else _decimal_text(
                self.standard_uncertainty_text,
                "standard_uncertainty_text",
            )
        )
        missing = (
            None
            if self.missing_reason is None
            else _text(
                self.missing_reason,
                "missing_reason",
            )
        )
        if estimate is None:
            if uncertainty is not None or missing is None:
                raise MissingChemicalContractError(
                    "missing estimates require missing_reason and no uncertainty"
                )
        elif uncertainty is None or missing is not None:
            raise MissingChemicalContractError(
                "observed estimates require uncertainty and no missing_reason"
            )
        if not isinstance(self.tie, bool):
            raise MissingChemicalContractError("tie must be boolean")
        object.__setattr__(self, "estimate_value_text", estimate)
        object.__setattr__(self, "standard_uncertainty_text", uncertainty)
        object.__setattr__(self, "missing_reason", missing)

    def as_dict(self) -> dict[str, Any]:
        return {
            "criterion_id": self.criterion_id,
            "estimate_value_text": self.estimate_value_text,
            "standard_uncertainty_text": self.standard_uncertainty_text,
            "unit": self.unit,
            "tie": self.tie,
            "missing_reason": self.missing_reason,
        }


def _criterion_is_met(
    criterion: DecisionCriterion,
    outcome: CriterionOutcome,
) -> bool | None:
    if outcome.estimate_value_text is None or outcome.tie:
        return None
    estimate = Decimal(outcome.estimate_value_text)
    uncertainty = Decimal(outcome.standard_uncertainty_text or "0")
    lower = estimate - uncertainty
    upper = estimate + uncertainty
    threshold = Decimal(criterion.threshold_value_text)
    if criterion.direction is CriterionDirection.AT_LEAST:
        return lower >= threshold
    if criterion.direction is CriterionDirection.AT_MOST:
        return upper <= threshold
    if criterion.direction is CriterionDirection.DIFFERENCE:
        if lower <= 0 <= upper:
            lower_magnitude = Decimal("0")
        else:
            lower_magnitude = min(abs(lower), abs(upper))
        return lower_magnitude >= threshold and lower_magnitude > 0
    margin = Decimal(criterion.equivalence_margin_text or "0")
    return lower >= threshold - margin and upper <= threshold + margin


@dataclass(frozen=True, slots=True)
class MissingChemicalDecisionReceipt:
    receipt_id: str
    protocol: InitVar[MissingChemicalComparisonProtocol]
    evidence: InitVar[ComparisonEvidenceBundle]
    decision: ImpactDecision
    outcomes: tuple[CriterionOutcome, ...]
    reviewer_evidence_sha256: str
    protocol_sha256: str = field(init=False)
    evidence_bundle_sha256: str = field(init=False)
    criterion_evaluations: tuple[tuple[str, bool | None], ...] = field(init=False)
    formula_authority: bool = field(default=False, init=False)
    inventory_authority: bool = field(default=False, init=False)
    purchase_authority: bool = field(default=False, init=False)
    execution_authorized: bool = field(default=False, init=False)
    scientific_authority: bool = field(default=False, init=False)
    oav_authority: bool = field(default=False, init=False)
    sensory_authority: bool = field(default=False, init=False)
    safety_authority: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)

    def __post_init__(
        self,
        protocol: MissingChemicalComparisonProtocol,
        evidence: ComparisonEvidenceBundle,
    ) -> None:
        object.__setattr__(self, "receipt_id", _identifier(self.receipt_id, "receipt_id"))
        if protocol.state is not ImpactPlanState.PROTOCOL_LOCKED:
            raise MissingChemicalContractError("decision requires a locked protocol")
        if evidence.protocol_sha256 != protocol.content_sha256:
            raise MissingChemicalContractError("decision evidence is bound to a different protocol")
        decision = ImpactDecision(self.decision)
        outcomes = tuple(sorted(self.outcomes, key=lambda item: item.criterion_id))
        if any(not isinstance(item, CriterionOutcome) for item in outcomes):
            raise MissingChemicalContractError("outcomes must contain CriterionOutcome values")
        expected = tuple(item.criterion_id for item in protocol.criteria)
        observed = tuple(item.criterion_id for item in outcomes)
        if observed != expected:
            raise MissingChemicalContractError(
                "decision must preserve one outcome for every locked criterion"
            )
        criteria_by_id = {item.criterion_id: item for item in protocol.criteria}
        evaluations: list[tuple[str, bool | None]] = []
        for outcome in outcomes:
            criterion = criteria_by_id[outcome.criterion_id]
            if outcome.unit != criterion.unit:
                raise MissingChemicalContractError(
                    f"outcome {outcome.criterion_id} unit does not match its criterion"
                )
            evaluations.append((outcome.criterion_id, _criterion_is_met(criterion, outcome)))
        has_missing_or_tie = (
            any(item.estimate_value_text is None or item.tie for item in outcomes)
            or evidence.governed_missing_count > 0
        )
        if has_missing_or_tie and decision not in {
            ImpactDecision.HOLD,
            ImpactDecision.INCONCLUSIVE,
        }:
            raise MissingChemicalContractError(
                "missing or tied outcomes cannot support a directional decision"
            )
        evaluation_values = tuple(item[1] for item in evaluations)
        if decision is ImpactDecision.SUPPORTS_FURTHER_REVIEW and (
            not evaluation_values or not all(item is True for item in evaluation_values)
        ):
            raise MissingChemicalContractError(
                "SUPPORTS_FURTHER_REVIEW requires every locked criterion to be met"
            )
        if decision is ImpactDecision.REJECT_REDUNDANT and (
            not evaluation_values
            or any(item is None for item in evaluation_values)
            or all(item is True for item in evaluation_values)
        ):
            raise MissingChemicalContractError(
                "REJECT_REDUNDANT requires complete evidence and at least one unmet criterion"
            )
        object.__setattr__(self, "decision", decision)
        object.__setattr__(self, "outcomes", outcomes)
        object.__setattr__(self, "criterion_evaluations", tuple(evaluations))
        object.__setattr__(
            self,
            "reviewer_evidence_sha256",
            _sha256(self.reviewer_evidence_sha256, "reviewer_evidence_sha256"),
        )
        object.__setattr__(self, "protocol_sha256", protocol.content_sha256)
        object.__setattr__(
            self,
            "evidence_bundle_sha256",
            evidence.content_sha256,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "perfume-chem-missing-chemical-decision-receipt-v1",
            "receipt_id": self.receipt_id,
            "protocol_sha256": self.protocol_sha256,
            "evidence_bundle_sha256": self.evidence_bundle_sha256,
            "decision": self.decision.value,
            "outcomes": [item.as_dict() for item in self.outcomes],
            "criterion_evaluations": [
                {"criterion_id": criterion_id, "met": met}
                for criterion_id, met in self.criterion_evaluations
            ],
            "reviewer_evidence_sha256": self.reviewer_evidence_sha256,
            "formula_authority": self.formula_authority,
            "inventory_authority": self.inventory_authority,
            "purchase_authority": self.purchase_authority,
            "execution_authorized": self.execution_authorized,
            "scientific_authority": self.scientific_authority,
            "oav_authority": self.oav_authority,
            "sensory_authority": self.sensory_authority,
            "safety_authority": self.safety_authority,
            "release_authority": self.release_authority,
        }

    @property
    def receipt_sha256(self) -> str:
        return canonical_sha256(self.as_dict())


__all__ = [
    "BlindedAllocation",
    "CandidateInventoryStatus",
    "ComparisonArmBinding",
    "ComparisonArmKind",
    "ComparisonEvidenceBundle",
    "ComparisonProtocolBindings",
    "CriterionDirection",
    "CriterionOutcome",
    "DecisionCriterion",
    "ExpectedObservationCell",
    "ExpectedObservationManifest",
    "FormulaForkManifest",
    "FormulaForkRecord",
    "ImpactClassification",
    "ImpactCandidateIdentityBinding",
    "ImpactDecision",
    "ImpactPlanState",
    "MissingChemicalAssessment",
    "MissingChemicalComparisonProtocol",
    "MissingChemicalContractError",
    "MissingChemicalDecisionReceipt",
    "NativeLineageBinding",
    "ObservationCellStatus",
    "ObservationReceiptBinding",
    "ProtocolProjectionAuthorization",
    "QualificationReceiptBinding",
    "QualitativeImpactCandidate",
    "SourceIntegrationState",
    "StockReceiptBinding",
    "project_lab_experiment_protocol_json",
]
