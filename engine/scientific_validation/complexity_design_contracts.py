"""Native, non-authoritative design contracts for complexity-model discovery.

These contracts close three narrow design gaps without creating another
pipeline or persistence owner:

* exact causal-isolate checks over canonical formula dose receipts;
* separate portfolio-signature views with no sensory-similarity threshold;
* n-ary interaction evidence states that cannot be promoted from pair records.

The calculations are deterministic diagnostics.  They do not mutate formulas,
inventory, experiments, observations, or model admission state, and they never
grant physical, sensory, safety, or release authority.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any

from engine.calibration.hashing import stable_json_hash
from engine.pipeline.preflight import FormulaDoseReceipt
from engine.scientific_validation.complexity_model_admission import OAVGateBinding

_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")


def _text(value: object, field_name: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be blank")
    return normalized


def _sha256(value: object, field_name: str) -> str:
    normalized = _text(value, field_name).lower()
    if _SHA256_RE.fullmatch(normalized) is None:
        raise ValueError(f"{field_name} must be a lowercase SHA-256 digest")
    return normalized


def _decimal(value: object, field_name: str, *, allow_zero: bool = True) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, Decimal) or not value.is_finite():
        raise TypeError(f"{field_name} must be a finite Decimal")
    if value < 0 or (not allow_zero and value == 0):
        qualifier = "nonnegative" if allow_zero else "greater than zero"
        raise ValueError(f"{field_name} must be {qualifier}")
    return value


def _unique_text(values: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    normalized = tuple(_text(value, field_name) for value in values)
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{field_name} must contain unique values")
    return normalized


def _decimal_text(value: Decimal) -> str:
    return format(value, "f")


class CausalArmRole(str, Enum):
    NULL = "NULL"
    INTERMEDIATE = "INTERMEDIATE"
    FULL = "FULL"


class CausalIsolateState(str, Enum):
    DESIGN_READY = "DESIGN_READY"
    REBUILD = "REBUILD"


class SignatureComparisonState(str, Enum):
    COMPLETE_DIAGNOSTIC = "COMPLETE_DIAGNOSTIC"
    PARTIAL_ABSTENTION = "PARTIAL_ABSTENTION"


class NaryEvidenceState(str, Enum):
    HYPOTHESIS = "HYPOTHESIS"
    EXPERIMENT_DESIGN = "EXPERIMENT_DESIGN"
    OBSERVED_SCOPE = "OBSERVED_SCOPE"


class NaryAssessmentState(str, Enum):
    HYPOTHESIS_ONLY = "HYPOTHESIS_ONLY"
    DESIGN_READY = "DESIGN_READY"
    OBSERVATION_SCOPE_CANDIDATE = "OBSERVATION_SCOPE_CANDIDATE"
    HOLD = "HOLD"


@dataclass(frozen=True, slots=True)
class CausalInvariant:
    invariant_id: str
    value_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "invariant_id", _text(self.invariant_id, "invariant_id"))
        object.__setattr__(self, "value_sha256", _sha256(self.value_sha256, "value_sha256"))

    def as_dict(self) -> dict[str, str]:
        return {
            "invariant_id": self.invariant_id,
            "value_sha256": self.value_sha256,
        }


@dataclass(frozen=True, slots=True)
class CausalIsolateArm:
    arm_id: str
    role: CausalArmRole
    axis_level: Decimal
    formula_sha256: str
    dose_receipt_sha256: str
    supplied_stock_total_ul: Decimal
    active_equivalent_total_ul: Decimal
    carrier_total_ul: Decimal
    invariants: tuple[CausalInvariant, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "arm_id", _text(self.arm_id, "arm_id"))
        if not isinstance(self.role, CausalArmRole):
            raise TypeError("role must be a CausalArmRole")
        _decimal(self.axis_level, "axis_level")
        object.__setattr__(self, "formula_sha256", _sha256(self.formula_sha256, "formula_sha256"))
        object.__setattr__(
            self,
            "dose_receipt_sha256",
            _sha256(self.dose_receipt_sha256, "dose_receipt_sha256"),
        )
        _decimal(self.supplied_stock_total_ul, "supplied_stock_total_ul", allow_zero=False)
        _decimal(self.active_equivalent_total_ul, "active_equivalent_total_ul", allow_zero=False)
        _decimal(self.carrier_total_ul, "carrier_total_ul")
        if self.active_equivalent_total_ul > self.supplied_stock_total_ul:
            raise ValueError("active equivalent total cannot exceed supplied stock total")
        if self.active_equivalent_total_ul + self.carrier_total_ul != self.supplied_stock_total_ul:
            raise ValueError("active equivalent plus carrier must equal supplied stock total")
        invariant_ids = tuple(item.invariant_id for item in self.invariants)
        if len(invariant_ids) != len(set(invariant_ids)):
            raise ValueError("invariants must contain unique invariant IDs")

    @classmethod
    def from_dose_receipt(
        cls,
        *,
        arm_id: str,
        role: CausalArmRole,
        axis_level: Decimal,
        receipt: FormulaDoseReceipt,
        invariants: tuple[CausalInvariant, ...],
    ) -> CausalIsolateArm:
        """Bind one arm to the canonical planned-volume dose receipt."""

        if not isinstance(receipt, FormulaDoseReceipt):
            raise TypeError("receipt must be a FormulaDoseReceipt")
        if receipt.status != "BOUND":
            raise ValueError("causal isolate arms require a BOUND formula dose receipt")
        if any(line.active_ul is None or line.status != "BOUND" for line in receipt.lines):
            raise ValueError("causal isolate arms require every dose line to be bound")
        supplied = sum((Decimal(str(line.raw_ul)) for line in receipt.lines), Decimal("0"))
        active = sum(
            (Decimal(str(line.active_ul)) for line in receipt.lines if line.active_ul is not None),
            Decimal("0"),
        )
        return cls(
            arm_id=arm_id,
            role=role,
            axis_level=axis_level,
            formula_sha256=receipt.legacy_formula_hash,
            dose_receipt_sha256=receipt.receipt_sha256,
            supplied_stock_total_ul=supplied,
            active_equivalent_total_ul=active,
            carrier_total_ul=supplied - active,
            invariants=invariants,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "arm_id": self.arm_id,
            "role": self.role.value,
            "axis_level": _decimal_text(self.axis_level),
            "formula_sha256": self.formula_sha256,
            "dose_receipt_sha256": self.dose_receipt_sha256,
            "supplied_stock_total_ul": _decimal_text(self.supplied_stock_total_ul),
            "active_equivalent_total_ul": _decimal_text(self.active_equivalent_total_ul),
            "carrier_total_ul": _decimal_text(self.carrier_total_ul),
            "invariants": [item.as_dict() for item in self.invariants],
        }


@dataclass(frozen=True, slots=True)
class CausalIsolateDesign:
    model_id: str
    manipulated_axis_id: str
    arms: tuple[CausalIsolateArm, ...]
    required_invariant_ids: tuple[str, ...]
    active_equivalence_required: bool = field(default=True, init=False)
    formula_mutation_authorized: bool = field(default=False, init=False)
    physical_execution_authorized: bool = field(default=False, init=False)
    sensory_authority: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "model_id", _text(self.model_id, "model_id"))
        object.__setattr__(
            self,
            "manipulated_axis_id",
            _text(self.manipulated_axis_id, "manipulated_axis_id"),
        )
        if len(self.arms) < 2:
            raise ValueError("a causal isolate requires at least two arms")
        arm_ids = tuple(item.arm_id for item in self.arms)
        if len(arm_ids) != len(set(arm_ids)):
            raise ValueError("causal isolate arm IDs must be unique")
        object.__setattr__(
            self,
            "required_invariant_ids",
            _unique_text(self.required_invariant_ids, "required_invariant_ids"),
        )
        if not self.required_invariant_ids:
            raise ValueError("required_invariant_ids must not be empty")

    def as_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "manipulated_axis_id": self.manipulated_axis_id,
            "arms": [item.as_dict() for item in self.arms],
            "required_invariant_ids": list(self.required_invariant_ids),
            "active_equivalence_required": self.active_equivalence_required,
            "formula_mutation_authorized": self.formula_mutation_authorized,
            "physical_execution_authorized": self.physical_execution_authorized,
            "sensory_authority": self.sensory_authority,
            "release_authority": self.release_authority,
        }

    @property
    def design_sha256(self) -> str:
        return stable_json_hash(self.as_dict())


@dataclass(frozen=True, slots=True)
class CausalIsolateAssessment:
    state: CausalIsolateState
    design_sha256: str
    blockers: tuple[str, ...]
    evidence_scope: str = field(default="EXPERIMENT_DESIGN_ONLY", init=False)
    empirical_authority: bool = field(default=False, init=False)
    formula_mutation_authorized: bool = field(default=False, init=False)
    physical_execution_authorized: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)

    def as_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "design_sha256": self.design_sha256,
            "blockers": list(self.blockers),
            "evidence_scope": self.evidence_scope,
            "empirical_authority": self.empirical_authority,
            "formula_mutation_authorized": self.formula_mutation_authorized,
            "physical_execution_authorized": self.physical_execution_authorized,
            "release_authority": self.release_authority,
        }


def evaluate_causal_isolate(design: CausalIsolateDesign) -> CausalIsolateAssessment:
    """Check null/full structure and exact planned-dose invariants."""

    if not isinstance(design, CausalIsolateDesign):
        raise TypeError("design must be a CausalIsolateDesign")
    blockers: list[str] = []
    null_arms = tuple(item for item in design.arms if item.role is CausalArmRole.NULL)
    full_arms = tuple(item for item in design.arms if item.role is CausalArmRole.FULL)
    intermediate = tuple(item for item in design.arms if item.role is CausalArmRole.INTERMEDIATE)
    if len(null_arms) != 1:
        blockers.append("exactly one NULL arm is required")
    if len(full_arms) != 1:
        blockers.append("exactly one FULL arm is required")
    if len(null_arms) == 1 and null_arms[0].axis_level != Decimal("0"):
        blockers.append("the NULL arm axis level must be exactly zero")
    if len(full_arms) == 1 and full_arms[0].axis_level <= Decimal("0"):
        blockers.append("the FULL arm axis level must be greater than zero")
    if len({item.axis_level for item in design.arms}) != len(design.arms):
        blockers.append("axis levels must be unique across arms")
    if null_arms and full_arms:
        low = null_arms[0].axis_level
        high = full_arms[0].axis_level
        if any(not low < item.axis_level < high for item in intermediate):
            blockers.append("INTERMEDIATE axis levels must lie between NULL and FULL")

    for label, values in (
        (
            "supplied stock total",
            {item.supplied_stock_total_ul for item in design.arms},
        ),
        (
            "active-equivalent total",
            {item.active_equivalent_total_ul for item in design.arms},
        ),
        ("carrier total", {item.carrier_total_ul for item in design.arms}),
    ):
        if len(values) != 1:
            blockers.append(f"{label} must remain exactly invariant across arms")
    if len({item.formula_sha256 for item in design.arms}) != len(design.arms):
        blockers.append("each arm requires a distinct formula hash")
    if len({item.dose_receipt_sha256 for item in design.arms}) != len(design.arms):
        blockers.append("each arm requires a distinct dose receipt hash")

    expected_values: dict[str, str] = {}
    for arm in design.arms:
        by_id = {item.invariant_id: item.value_sha256 for item in arm.invariants}
        missing = set(design.required_invariant_ids).difference(by_id)
        if missing:
            blockers.append(f"{arm.arm_id} is missing invariants: {', '.join(sorted(missing))}")
        for invariant_id in design.required_invariant_ids:
            if invariant_id not in by_id:
                continue
            prior = expected_values.setdefault(invariant_id, by_id[invariant_id])
            if by_id[invariant_id] != prior:
                blockers.append(f"{invariant_id} differs across causal-isolate arms")

    return CausalIsolateAssessment(
        state=(CausalIsolateState.REBUILD if blockers else CausalIsolateState.DESIGN_READY),
        design_sha256=design.design_sha256,
        blockers=tuple(dict.fromkeys(blockers)),
    )


@dataclass(frozen=True, slots=True)
class FormulaSignatureComponent:
    component_id: str
    supplied_stock_amount: Decimal
    active_equivalent_amount: Decimal | None
    sensory_system_ids: tuple[str, ...] = ()
    recognizer_ids: tuple[str, ...] = ()
    phase_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "component_id", _text(self.component_id, "component_id"))
        _decimal(self.supplied_stock_amount, "supplied_stock_amount", allow_zero=False)
        if self.active_equivalent_amount is not None:
            _decimal(self.active_equivalent_amount, "active_equivalent_amount")
            if self.active_equivalent_amount > self.supplied_stock_amount:
                raise ValueError("active equivalent amount cannot exceed supplied stock amount")
        for field_name in ("sensory_system_ids", "recognizer_ids", "phase_ids"):
            object.__setattr__(
                self,
                field_name,
                _unique_text(getattr(self, field_name), field_name),
            )

    def as_dict(self) -> dict[str, Any]:
        return {
            "component_id": self.component_id,
            "supplied_stock_amount": _decimal_text(self.supplied_stock_amount),
            "active_equivalent_amount": (
                _decimal_text(self.active_equivalent_amount)
                if self.active_equivalent_amount is not None
                else None
            ),
            "sensory_system_ids": list(self.sensory_system_ids),
            "recognizer_ids": list(self.recognizer_ids),
            "phase_ids": list(self.phase_ids),
        }


@dataclass(frozen=True, slots=True)
class FormulaSignature:
    formula_sha256: str
    dose_receipt_sha256: str
    quantity_basis: str
    components: tuple[FormulaSignatureComponent, ...]
    formula_authority: bool = field(default=False, init=False)
    sensory_similarity_authority: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "formula_sha256", _sha256(self.formula_sha256, "formula_sha256"))
        object.__setattr__(
            self,
            "dose_receipt_sha256",
            _sha256(self.dose_receipt_sha256, "dose_receipt_sha256"),
        )
        object.__setattr__(self, "quantity_basis", _text(self.quantity_basis, "quantity_basis"))
        if not self.components:
            raise ValueError("a formula signature requires at least one component")
        component_ids = tuple(item.component_id for item in self.components)
        if len(component_ids) != len(set(component_ids)):
            raise ValueError("formula signature component IDs must be unique")

    @classmethod
    def from_dose_receipt(
        cls,
        receipt: FormulaDoseReceipt,
        *,
        sensory_system_ids: Mapping[str, tuple[str, ...]] | None = None,
        recognizer_ids: Mapping[str, tuple[str, ...]] | None = None,
        phase_ids: Mapping[str, tuple[str, ...]] | None = None,
    ) -> FormulaSignature:
        """Project one canonical dose receipt without inventing mass authority."""

        if not isinstance(receipt, FormulaDoseReceipt):
            raise TypeError("receipt must be a FormulaDoseReceipt")
        if receipt.status != "BOUND":
            raise ValueError("formula signatures require a BOUND formula dose receipt")
        systems = sensory_system_ids or {}
        recognizers = recognizer_ids or {}
        phases = phase_ids or {}
        return cls(
            formula_sha256=receipt.legacy_formula_hash,
            dose_receipt_sha256=receipt.receipt_sha256,
            quantity_basis="PLANNED_VOLUME_UL",
            components=tuple(
                FormulaSignatureComponent(
                    component_id=line.material_name,
                    supplied_stock_amount=Decimal(str(line.raw_ul)),
                    active_equivalent_amount=(
                        Decimal(str(line.active_ul)) if line.active_ul is not None else None
                    ),
                    sensory_system_ids=tuple(systems.get(line.material_name, ())),
                    recognizer_ids=tuple(recognizers.get(line.material_name, ())),
                    phase_ids=tuple(phases.get(line.material_name, ())),
                )
                for line in receipt.lines
            ),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "formula_sha256": self.formula_sha256,
            "dose_receipt_sha256": self.dose_receipt_sha256,
            "quantity_basis": self.quantity_basis,
            "components": [item.as_dict() for item in self.components],
            "formula_authority": self.formula_authority,
            "sensory_similarity_authority": self.sensory_similarity_authority,
            "release_authority": self.release_authority,
        }

    @property
    def signature_sha256(self) -> str:
        return stable_json_hash(self.as_dict())


@dataclass(frozen=True, slots=True)
class FormulaSignatureComparison:
    state: SignatureComparisonState
    left_signature_sha256: str
    right_signature_sha256: str
    material_overlap_jaccard: Decimal
    supplied_stock_cosine: Decimal
    active_equivalent_cosine: Decimal | None
    sensory_system_overlap_jaccard: Decimal | None
    recognizer_overlap_jaccard: Decimal | None
    phase_overlap_jaccard: Decimal | None
    abstentions: tuple[str, ...]
    threshold_applied: bool = field(default=False, init=False)
    sensory_similarity_authority: bool = field(default=False, init=False)
    portfolio_nonredundancy_authority: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)

    def as_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "left_signature_sha256": self.left_signature_sha256,
            "right_signature_sha256": self.right_signature_sha256,
            "material_overlap_jaccard": _decimal_text(self.material_overlap_jaccard),
            "supplied_stock_cosine": _decimal_text(self.supplied_stock_cosine),
            "active_equivalent_cosine": (
                _decimal_text(self.active_equivalent_cosine)
                if self.active_equivalent_cosine is not None
                else None
            ),
            "sensory_system_overlap_jaccard": (
                _decimal_text(self.sensory_system_overlap_jaccard)
                if self.sensory_system_overlap_jaccard is not None
                else None
            ),
            "recognizer_overlap_jaccard": (
                _decimal_text(self.recognizer_overlap_jaccard)
                if self.recognizer_overlap_jaccard is not None
                else None
            ),
            "phase_overlap_jaccard": (
                _decimal_text(self.phase_overlap_jaccard)
                if self.phase_overlap_jaccard is not None
                else None
            ),
            "abstentions": list(self.abstentions),
            "threshold_applied": self.threshold_applied,
            "sensory_similarity_authority": self.sensory_similarity_authority,
            "portfolio_nonredundancy_authority": self.portfolio_nonredundancy_authority,
            "release_authority": self.release_authority,
        }


def _jaccard(left: set[str], right: set[str]) -> Decimal | None:
    union = left | right
    if not union:
        return None
    return Decimal(len(left & right)) / Decimal(len(union))


def _cosine(left: Mapping[str, Decimal], right: Mapping[str, Decimal]) -> Decimal:
    names = set(left) | set(right)
    dot = sum(
        (left.get(name, Decimal("0")) * right.get(name, Decimal("0")) for name in names),
        Decimal("0"),
    )
    left_norm = sum((left.get(name, Decimal("0")) ** 2 for name in names), Decimal("0")).sqrt()
    right_norm = sum((right.get(name, Decimal("0")) ** 2 for name in names), Decimal("0")).sqrt()
    if left_norm == 0 or right_norm == 0:
        return Decimal("0")
    return dot / (left_norm * right_norm)


def compare_formula_signatures(
    left: FormulaSignature,
    right: FormulaSignature,
) -> FormulaSignatureComparison:
    """Return separate structural views; never collapse them to a pass/fail score."""

    if not isinstance(left, FormulaSignature) or not isinstance(right, FormulaSignature):
        raise TypeError("left and right must be FormulaSignature values")
    if left.quantity_basis != right.quantity_basis:
        raise ValueError("formula signatures require the same quantity basis")
    left_by_id = {item.component_id: item for item in left.components}
    right_by_id = {item.component_id: item for item in right.components}
    material_overlap = _jaccard(set(left_by_id), set(right_by_id))
    if material_overlap is None:  # pragma: no cover - signatures require components
        raise RuntimeError("formula signature material overlap is undefined")
    supplied = _cosine(
        {name: item.supplied_stock_amount for name, item in left_by_id.items()},
        {name: item.supplied_stock_amount for name, item in right_by_id.items()},
    )
    abstentions: list[str] = []
    active: Decimal | None
    if any(item.active_equivalent_amount is None for item in (*left.components, *right.components)):
        active = None
        abstentions.append("active-equivalent view withheld because at least one amount is unbound")
    else:
        active = _cosine(
            {
                name: item.active_equivalent_amount or Decimal("0")
                for name, item in left_by_id.items()
            },
            {
                name: item.active_equivalent_amount or Decimal("0")
                for name, item in right_by_id.items()
            },
        )

    overlap_views: list[tuple[str, Decimal | None]] = []
    for label, attribute in (
        ("sensory-system", "sensory_system_ids"),
        ("recognizer", "recognizer_ids"),
        ("phase", "phase_ids"),
    ):
        left_tags = {tag for item in left.components for tag in getattr(item, attribute)}
        right_tags = {tag for item in right.components for tag in getattr(item, attribute)}
        value = _jaccard(left_tags, right_tags)
        if value is None:
            abstentions.append(f"{label} view withheld because no tags are bound")
        overlap_views.append((label, value))
    overlap_by_name = dict(overlap_views)
    return FormulaSignatureComparison(
        state=(
            SignatureComparisonState.PARTIAL_ABSTENTION
            if abstentions
            else SignatureComparisonState.COMPLETE_DIAGNOSTIC
        ),
        left_signature_sha256=left.signature_sha256,
        right_signature_sha256=right.signature_sha256,
        material_overlap_jaccard=material_overlap,
        supplied_stock_cosine=supplied,
        active_equivalent_cosine=active,
        sensory_system_overlap_jaccard=overlap_by_name["sensory-system"],
        recognizer_overlap_jaccard=overlap_by_name["recognizer"],
        phase_overlap_jaccard=overlap_by_name["phase"],
        abstentions=tuple(abstentions),
    )


@dataclass(frozen=True, slots=True)
class NaryParticipant:
    material_id: str
    role: str
    ratio: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(self, "material_id", _text(self.material_id, "material_id"))
        object.__setattr__(self, "role", _text(self.role, "role"))
        _decimal(self.ratio, "ratio", allow_zero=False)

    def as_dict(self) -> dict[str, str]:
        return {
            "material_id": self.material_id,
            "role": self.role,
            "ratio": _decimal_text(self.ratio),
        }


@dataclass(frozen=True, slots=True)
class NaryInteractionCandidate:
    interaction_id: str
    evidence_state: NaryEvidenceState
    participants: tuple[NaryParticipant, ...]
    formula_sha256: str
    formula_signature_sha256: str
    matrix_sha256: str
    pairwise_evidence_refs: tuple[str, ...] = ()
    causal_isolate_sha256: str | None = None
    experiment_design_sha256: str | None = None
    experiment_execution_sha256: str | None = None
    observation_receipt_sha256s: tuple[str, ...] = ()
    oav_binding: OAVGateBinding | None = None
    formula_mutation_authorized: bool = field(default=False, init=False)
    empirical_promotion_authorized: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "interaction_id", _text(self.interaction_id, "interaction_id"))
        if not isinstance(self.evidence_state, NaryEvidenceState):
            raise TypeError("evidence_state must be a NaryEvidenceState")
        if len(self.participants) < 3:
            raise ValueError("n-ary interactions require at least three participants")
        material_ids = tuple(item.material_id for item in self.participants)
        if len(material_ids) != len(set(material_ids)):
            raise ValueError("n-ary participant material IDs must be unique")
        if sum((item.ratio for item in self.participants), Decimal("0")) != Decimal("1"):
            raise ValueError("n-ary participant ratios must sum exactly to one")
        for field_name in ("formula_sha256", "formula_signature_sha256", "matrix_sha256"):
            object.__setattr__(self, field_name, _sha256(getattr(self, field_name), field_name))
        object.__setattr__(
            self,
            "pairwise_evidence_refs",
            _unique_text(self.pairwise_evidence_refs, "pairwise_evidence_refs"),
        )
        for field_name in (
            "causal_isolate_sha256",
            "experiment_design_sha256",
            "experiment_execution_sha256",
        ):
            value = getattr(self, field_name)
            if value is not None:
                object.__setattr__(self, field_name, _sha256(value, field_name))
        object.__setattr__(
            self,
            "observation_receipt_sha256s",
            tuple(
                _sha256(value, "observation_receipt_sha256s")
                for value in self.observation_receipt_sha256s
            ),
        )
        if len(self.observation_receipt_sha256s) != len(set(self.observation_receipt_sha256s)):
            raise ValueError("observation receipt hashes must be unique")
        if self.oav_binding is not None and not isinstance(self.oav_binding, OAVGateBinding):
            raise TypeError("oav_binding must be an OAVGateBinding")

    def as_dict(self) -> dict[str, Any]:
        return {
            "interaction_id": self.interaction_id,
            "evidence_state": self.evidence_state.value,
            "participants": [item.as_dict() for item in self.participants],
            "formula_sha256": self.formula_sha256,
            "formula_signature_sha256": self.formula_signature_sha256,
            "matrix_sha256": self.matrix_sha256,
            "pairwise_evidence_refs": list(self.pairwise_evidence_refs),
            "causal_isolate_sha256": self.causal_isolate_sha256,
            "experiment_design_sha256": self.experiment_design_sha256,
            "experiment_execution_sha256": self.experiment_execution_sha256,
            "observation_receipt_sha256s": list(self.observation_receipt_sha256s),
            "oav_binding": self.oav_binding.as_dict() if self.oav_binding else None,
            "formula_mutation_authorized": self.formula_mutation_authorized,
            "empirical_promotion_authorized": self.empirical_promotion_authorized,
            "release_authority": self.release_authority,
        }

    @property
    def candidate_sha256(self) -> str:
        return stable_json_hash(self.as_dict())


@dataclass(frozen=True, slots=True)
class NaryInteractionAssessment:
    state: NaryAssessmentState
    candidate_sha256: str
    blockers: tuple[str, ...]
    pairwise_promotion_blocked: bool = field(default=True, init=False)
    sensory_authority: bool = field(default=False, init=False)
    empirical_model_authority: bool = field(default=False, init=False)
    formula_mutation_authorized: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)

    def as_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "candidate_sha256": self.candidate_sha256,
            "blockers": list(self.blockers),
            "pairwise_promotion_blocked": self.pairwise_promotion_blocked,
            "sensory_authority": self.sensory_authority,
            "empirical_model_authority": self.empirical_model_authority,
            "formula_mutation_authorized": self.formula_mutation_authorized,
            "release_authority": self.release_authority,
        }


def evaluate_nary_interaction(
    candidate: NaryInteractionCandidate,
) -> NaryInteractionAssessment:
    """Enforce evidence-state separation for one formula-specific hyperedge."""

    if not isinstance(candidate, NaryInteractionCandidate):
        raise TypeError("candidate must be a NaryInteractionCandidate")
    blockers: list[str] = []
    empirical_fields_present = bool(
        candidate.experiment_execution_sha256 or candidate.observation_receipt_sha256s
    )
    if candidate.evidence_state is NaryEvidenceState.HYPOTHESIS:
        if candidate.causal_isolate_sha256 or candidate.experiment_design_sha256:
            blockers.append("HYPOTHESIS state cannot carry a performed design claim")
        if empirical_fields_present or candidate.oav_binding is not None:
            blockers.append("HYPOTHESIS state cannot carry observation or OAV evidence")
        desired_state = NaryAssessmentState.HYPOTHESIS_ONLY
    else:
        if candidate.causal_isolate_sha256 is None:
            blockers.append("a causal-isolate design hash is required")
        if candidate.experiment_design_sha256 is None:
            blockers.append("an experiment design receipt hash is required")
        if candidate.oav_binding is None:
            blockers.append("a formula-bound OAV screening receipt is required")
        else:
            if candidate.oav_binding.formula_sha256 != candidate.formula_sha256:
                blockers.append("OAV binding formula hash does not match the candidate")
            blockers.extend(candidate.oav_binding.screening_blockers)
        if candidate.evidence_state is NaryEvidenceState.EXPERIMENT_DESIGN:
            if empirical_fields_present:
                blockers.append("EXPERIMENT_DESIGN state cannot contain performed observations")
            desired_state = NaryAssessmentState.DESIGN_READY
        else:
            if candidate.experiment_execution_sha256 is None:
                blockers.append("OBSERVED_SCOPE requires an experiment execution receipt")
            if not candidate.observation_receipt_sha256s:
                blockers.append("OBSERVED_SCOPE requires performed observation receipts")
            desired_state = NaryAssessmentState.OBSERVATION_SCOPE_CANDIDATE

    if blockers:
        desired_state = NaryAssessmentState.HOLD
    return NaryInteractionAssessment(
        state=desired_state,
        candidate_sha256=candidate.candidate_sha256,
        blockers=tuple(dict.fromkeys(blockers)),
    )


__all__ = [
    "CausalArmRole",
    "CausalInvariant",
    "CausalIsolateArm",
    "CausalIsolateAssessment",
    "CausalIsolateDesign",
    "CausalIsolateState",
    "FormulaSignature",
    "FormulaSignatureComparison",
    "FormulaSignatureComponent",
    "NaryAssessmentState",
    "NaryEvidenceState",
    "NaryInteractionAssessment",
    "NaryInteractionCandidate",
    "NaryParticipant",
    "SignatureComparisonState",
    "compare_formula_signatures",
    "evaluate_causal_isolate",
    "evaluate_nary_interaction",
]
