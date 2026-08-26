"""Clean-room musk restraint and layered-design admission contract.

This module validates explicit design hypotheses. It neither recommends musks
nor grants formula, stock, physical, sensory, safety, OAV, or release authority.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace
from enum import Enum
from itertools import combinations
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from engine.perception.complexity_inventory import ComplexityInventoryCatalog

EXCEPTION_ONLY_MUSKS = frozenset({"tonalide", "macrolide", "musk ketone"})


class MuskRole(str, Enum):
    DEPTH = "DEPTH"
    PROJECTION = "PROJECTION"
    TEXTURE = "TEXTURE"
    TEMPORAL_BRIDGE = "TEMPORAL_BRIDGE"
    CHARACTER_ECHO = "CHARACTER_ECHO"
    FIXATION = "FIXATION"


class InventoryState(str, Enum):
    OWNED = "OWNED"
    PLANNED_ACQUISITION = "PLANNED_ACQUISITION"
    DEPLETED = "DEPLETED"
    MISSING = "MISSING"
    UNKNOWN = "UNKNOWN"


class ClaimStatus(str, Enum):
    EVIDENCE_SUPPORTED = "EVIDENCE_SUPPORTED"
    STRUCTURED_HYPOTHESIS = "STRUCTURED_HYPOTHESIS"
    PHYSICAL_TEST_REQUIRED = "PHYSICAL_TEST_REQUIRED"


def _clean(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name.replace('_', ' ')} must be nonblank")
    return " ".join(value.split())


def _material_key(value: str) -> str:
    return " ".join(value.split()).casefold()


def _set_clean(instance: object, field_name: str) -> None:
    object.__setattr__(
        instance,
        field_name,
        _clean(getattr(instance, field_name), field_name),
    )


def _require_tuple(value: object, field_name: str) -> None:
    if not isinstance(value, tuple):
        raise TypeError(f"{field_name} must be a tuple")


@dataclass(frozen=True, slots=True)
class MuskExceptionCall:
    material: str
    target_tonal_role: str
    why_alternatives_fail: str
    loss_if_omitted: str
    failure_mode: str
    omission_control: str
    alternative_control: str

    def __post_init__(self) -> None:
        for name in (
            "material",
            "target_tonal_role",
            "why_alternatives_fail",
            "loss_if_omitted",
            "failure_mode",
            "omission_control",
            "alternative_control",
        ):
            _set_clean(self, name)


@dataclass(frozen=True, slots=True)
class MuskTargetBrief:
    required_character: str
    unwanted_character: str
    temporal_behavior: str
    projection_intimacy: str
    texture: str
    system_connections: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "required_character",
            "unwanted_character",
            "temporal_behavior",
            "projection_intimacy",
            "texture",
        ):
            _set_clean(self, name)
        _require_tuple(self.system_connections, "system_connections")
        normalized = tuple(
            _clean(item, "system connection") for item in self.system_connections
        )
        if not normalized:
            raise ValueError("system connections must not be empty")
        object.__setattr__(self, "system_connections", normalized)


@dataclass(frozen=True, slots=True)
class MuskFingerprint:
    material: str
    exact_target_effect: str
    temporal_window: str
    texture_axis: str
    projection_axis: str
    character_axis: str
    interaction_risks: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    claim_status: ClaimStatus

    def __post_init__(self) -> None:
        for name in (
            "material",
            "exact_target_effect",
            "temporal_window",
            "texture_axis",
            "projection_axis",
            "character_axis",
        ):
            _set_clean(self, name)
        for name in ("interaction_risks", "evidence_refs"):
            values = getattr(self, name)
            _require_tuple(values, name)
            normalized = tuple(_clean(item, name) for item in values)
            if not normalized:
                raise ValueError(f"{name.replace('_', ' ')} must not be empty")
            object.__setattr__(self, name, normalized)
        if not isinstance(self.claim_status, ClaimStatus):
            raise TypeError("claim_status must be a ClaimStatus")


@dataclass(frozen=True, slots=True)
class PairwiseNonredundancy:
    material_a: str
    material_b: str
    distinct_function_a: str
    distinct_function_b: str
    loss_if_a_omitted: str
    loss_if_b_omitted: str
    collision_risk: str
    controlled_comparison: str

    def __post_init__(self) -> None:
        for name in (
            "material_a",
            "material_b",
            "distinct_function_a",
            "distinct_function_b",
            "loss_if_a_omitted",
            "loss_if_b_omitted",
            "collision_risk",
            "controlled_comparison",
        ):
            _set_clean(self, name)
        if _material_key(self.material_a) == _material_key(self.material_b):
            raise ValueError("pairwise materials must be different")

    @property
    def material_pair(self) -> tuple[str, str]:
        return tuple(sorted((_material_key(self.material_a), _material_key(self.material_b))))


@dataclass(frozen=True, slots=True)
class MuskCandidate:
    material: str
    role: MuskRole
    target_function: str
    why_nonredundant: str
    inventory_state: InventoryState
    exact_stock_ref: str | None
    exception: MuskExceptionCall | None = None
    fingerprint: MuskFingerprint | None = None

    def __post_init__(self) -> None:
        for name in ("material", "target_function", "why_nonredundant"):
            _set_clean(self, name)
        if not isinstance(self.role, MuskRole):
            raise TypeError("role must be a MuskRole")
        if not isinstance(self.inventory_state, InventoryState):
            raise TypeError("inventory_state must be an InventoryState")
        if self.exact_stock_ref is not None:
            object.__setattr__(
                self,
                "exact_stock_ref",
                _clean(self.exact_stock_ref, "exact_stock_ref"),
            )
        if (
            self.inventory_state
            in {InventoryState.PLANNED_ACQUISITION, InventoryState.MISSING}
            and self.exact_stock_ref is not None
        ):
            raise ValueError(
                f"{self.inventory_state.value} musk cannot have exact_stock_ref"
            )
        if self.exception is not None and not isinstance(
            self.exception, MuskExceptionCall
        ):
            raise TypeError("exception must be a MuskExceptionCall")
        if self.fingerprint is not None and not isinstance(
            self.fingerprint, MuskFingerprint
        ):
            raise TypeError("fingerprint must be a MuskFingerprint")


def bind_musk_inventory(
    candidate: MuskCandidate,
    catalog: ComplexityInventoryCatalog | None = None,
) -> MuskCandidate:
    """Bind one target-defined musk candidate without changing its design role."""

    if not isinstance(candidate, MuskCandidate):
        raise TypeError("candidate must be a MuskCandidate")
    if catalog is None:
        from engine.perception.complexity_inventory import (
            load_complexity_inventory_catalog,
        )

        catalog = load_complexity_inventory_catalog()
    from engine.perception.complexity_inventory import (
        InventoryAvailability,
        StockReadiness,
    )

    projection = catalog.project(candidate.material)
    if (
        projection.availability is InventoryAvailability.OWNED
        and projection.stock_readiness is StockReadiness.EXACT_STOCK_IDENTIFIED
    ):
        state = InventoryState.OWNED
        exact_stock_ref = projection.exact_stock_ref
    elif projection.availability is InventoryAvailability.OUT_OF_STOCK:
        state = InventoryState.DEPLETED
        exact_stock_ref = None
    elif projection.availability is InventoryAvailability.PLANNED_ACQUISITION:
        state = InventoryState.PLANNED_ACQUISITION
        exact_stock_ref = None
    elif projection.availability in {
        InventoryAvailability.MISSING,
        InventoryAvailability.FORBIDDEN,
        InventoryAvailability.UNLISTED,
    }:
        state = InventoryState.MISSING
        exact_stock_ref = None
    else:
        state = InventoryState.UNKNOWN
        exact_stock_ref = None
    return replace(
        candidate,
        inventory_state=state,
        exact_stock_ref=exact_stock_ref,
    )


@dataclass(frozen=True, slots=True)
class MuskDesignRequest:
    target_identity: str
    candidates: tuple[MuskCandidate, ...] = ()
    target_brief: MuskTargetBrief | None = None
    pairwise_nonredundancy: tuple[PairwiseNonredundancy, ...] = ()

    def __post_init__(self) -> None:
        _set_clean(self, "target_identity")
        _require_tuple(self.candidates, "candidates")
        _require_tuple(self.pairwise_nonredundancy, "pairwise_nonredundancy")
        if any(not isinstance(item, MuskCandidate) for item in self.candidates):
            raise TypeError("candidates must contain MuskCandidate values")
        if any(
            not isinstance(item, PairwiseNonredundancy)
            for item in self.pairwise_nonredundancy
        ):
            raise TypeError(
                "pairwise_nonredundancy must contain PairwiseNonredundancy values"
            )
        if self.target_brief is not None and not isinstance(
            self.target_brief, MuskTargetBrief
        ):
            raise TypeError("target_brief must be a MuskTargetBrief")


@dataclass(frozen=True, slots=True)
class MuskMaterialDecision:
    material: str
    target_included: bool
    current_build_included: bool
    disposition: str


@dataclass(frozen=True, slots=True)
class MuskDesignResult:
    state: str
    architecture_mode: str
    target_ideal_state: str
    current_inventory_build_state: str
    selected: tuple[MuskCandidate, ...]
    decisions: tuple[MuskMaterialDecision, ...]
    issue_codes: tuple[str, ...]
    source_admission_authority: bool = False
    formula_authority: bool = False
    inventory_authority: bool = False
    physical_execution_authorized: bool = False
    sensory_authority: bool = False
    safety_authority: bool = False
    oav_authority: bool = False
    release_authority: bool = False

    def as_dict(self) -> dict[str, Any]:
        return _to_json_value(self)


def _to_json_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return {
            item.name: _to_json_value(getattr(value, item.name)) for item in fields(value)
        }
    if isinstance(value, tuple):
        return [_to_json_value(item) for item in value]
    if isinstance(value, frozenset):
        return sorted(_to_json_value(item) for item in value)
    return value


def _append_once(target: list[str], code: str) -> None:
    if code not in target:
        target.append(code)


def _owned_with_identity(candidate: MuskCandidate) -> bool:
    return (
        candidate.inventory_state is InventoryState.OWNED
        and candidate.exact_stock_ref is not None
    )


def _inventory_disposition(candidate: MuskCandidate) -> str:
    if _owned_with_identity(candidate):
        return "BUILD_IDENTIFIED"
    if candidate.inventory_state is InventoryState.PLANNED_ACQUISITION:
        return "TARGET_ONLY_PLANNED_ACQUISITION"
    if candidate.inventory_state is InventoryState.MISSING:
        return "TARGET_ONLY_MISSING"
    if candidate.inventory_state is InventoryState.DEPLETED:
        return "TARGET_ONLY_DEPLETED"
    return "TARGET_ONLY_EXACT_STOCK_REQUIRED"


def evaluate_musk_design(request: MuskDesignRequest) -> MuskDesignResult:
    issues: list[str] = []
    decisions: list[MuskMaterialDecision] = []
    selected: list[MuskCandidate] = []

    candidate_keys = [_material_key(item.material) for item in request.candidates]
    duplicate_keys = {
        key for key in candidate_keys if candidate_keys.count(key) > 1
    }
    if duplicate_keys:
        _append_once(issues, "DUPLICATE_MUSK_MATERIAL")

    for candidate in request.candidates:
        material_key = _material_key(candidate.material)
        is_exception_only = material_key in EXCEPTION_ONLY_MUSKS
        if is_exception_only and candidate.exception is None:
            _append_once(issues, "MUSK_EXCEPTION_REQUIRED")
            decisions.append(
                MuskMaterialDecision(
                    candidate.material,
                    False,
                    False,
                    "OMITTED_EXCEPTION_REQUIRED",
                )
            )
            continue
        if candidate.exception is not None:
            if not is_exception_only:
                _append_once(issues, "UNEXPECTED_MUSK_EXCEPTION")
            elif _material_key(candidate.exception.material) != material_key:
                _append_once(issues, "MUSK_EXCEPTION_MATERIAL_MISMATCH")
                decisions.append(
                    MuskMaterialDecision(
                        candidate.material,
                        False,
                        False,
                        "OMITTED_EXCEPTION_MISMATCH",
                    )
                )
                continue
        if candidate.fingerprint is not None and _material_key(
            candidate.fingerprint.material
        ) != material_key:
            _append_once(issues, "MUSK_FINGERPRINT_MATERIAL_MISMATCH")
        selected.append(candidate)
        build_included = _owned_with_identity(candidate)
        decisions.append(
            MuskMaterialDecision(
                candidate.material,
                True,
                build_included,
                _inventory_disposition(candidate),
            )
        )

    if len(selected) > 1:
        roles = [item.role for item in selected]
        if len(roles) != len(set(roles)):
            _append_once(issues, "REDUNDANT_MUSK_ROLE")
        if request.target_brief is None:
            _append_once(issues, "MUSK_TARGET_BRIEF_REQUIRED")
        if any(item.fingerprint is None for item in selected):
            _append_once(issues, "MUSK_FINGERPRINT_REQUIRED")

        expected_pairs = {
            tuple(sorted((_material_key(a.material), _material_key(b.material))))
            for a, b in combinations(selected, 2)
        }
        supplied_pairs = [item.material_pair for item in request.pairwise_nonredundancy]
        if len(supplied_pairs) != len(set(supplied_pairs)):
            _append_once(issues, "DUPLICATE_PAIRWISE_NONREDUNDANCY")
        supplied_set = set(supplied_pairs)
        if expected_pairs.difference(supplied_set):
            _append_once(issues, "PAIRWISE_NONREDUNDANCY_MISSING")
        if supplied_set.difference(expected_pairs):
            _append_once(issues, "PAIRWISE_NONREDUNDANCY_UNEXPECTED")
    elif request.pairwise_nonredundancy:
        _append_once(issues, "PAIRWISE_NONREDUNDANCY_UNEXPECTED")

    if duplicate_keys:
        selected = [
            item for item in selected if _material_key(item.material) not in duplicate_keys
        ]

    architecture_mode = (
        "OMITTED"
        if not selected
        else "SPARSE"
        if len(selected) == 1
        else "LAYERED"
    )
    state = "HOLD" if issues else "PASS"
    if state == "HOLD":
        target_ideal_state = "HOLD"
    elif selected:
        target_ideal_state = "DESIGN_AVAILABLE"
    else:
        target_ideal_state = "OMITTED"

    if state == "HOLD" and not selected:
        current_build_state = "HOLD"
    elif not selected:
        current_build_state = "NOT_APPLICABLE"
    elif all(_owned_with_identity(item) for item in selected):
        current_build_state = "BUILD_IDENTIFIED"
    else:
        current_build_state = "HOLD_PROCUREMENT_REQUIRED"

    return MuskDesignResult(
        state=state,
        architecture_mode=architecture_mode,
        target_ideal_state=target_ideal_state,
        current_inventory_build_state=current_build_state,
        selected=tuple(selected),
        decisions=tuple(decisions),
        issue_codes=tuple(issues),
    )
