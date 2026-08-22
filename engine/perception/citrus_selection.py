"""Target-first citrus architecture selection without a beauty score.

The selector is deliberately pure: all candidate facts and inventory states are
explicit inputs. It never reads the legacy citrus scorer, supplier copy, or a
live inventory file, and it never treats frequency or material count as quality.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any

from engine.calibration.hashing import stable_json_hash

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be nonblank text")
    return value.strip()


def _unique_text(values: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise TypeError(f"{field_name} must be a tuple")
    normalized = tuple(_text(item, f"{field_name} item") for item in values)
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{field_name} must contain unique values")
    return normalized


class CitrusInventoryState(str, Enum):
    OWNED = "OWNED"
    OUT_OF_STOCK = "OUT_OF_STOCK"
    PLANNED_ACQUISITION = "PLANNED_ACQUISITION"
    VERIFY_FIRST = "VERIFY_FIRST"
    MISSING = "MISSING"


class CitrusCandidateScope(str, Enum):
    PRIMARY_OR_SUPPORT = "PRIMARY_OR_SUPPORT"
    SUPPORT_ONLY = "SUPPORT_ONLY"


class CitrusSelectionState(str, Enum):
    PASS = "PASS"
    HOLD = "HOLD"
    NONE = "NONE"


@dataclass(frozen=True, slots=True)
class CitrusCandidate:
    material: str
    roles: tuple[str, ...]
    axis_matches: tuple[str, ...]
    axis_conflicts: tuple[str, ...]
    inventory_state: CitrusInventoryState
    exact_stock_ref: str | None
    transition_to_heart: str
    evidence_refs: tuple[str, ...]
    selection_scope: CitrusCandidateScope = CitrusCandidateScope.PRIMARY_OR_SUPPORT

    def __post_init__(self) -> None:
        object.__setattr__(self, "material", _text(self.material, "material"))
        roles = _unique_text(self.roles, "roles")
        if not roles:
            raise ValueError("roles must not be empty")
        object.__setattr__(self, "roles", roles)
        matches = _unique_text(self.axis_matches, "axis_matches")
        conflicts = _unique_text(self.axis_conflicts, "axis_conflicts")
        if set(matches).intersection(conflicts):
            raise ValueError("axis_matches and axis_conflicts must not overlap")
        object.__setattr__(self, "axis_matches", matches)
        object.__setattr__(self, "axis_conflicts", conflicts)
        if not isinstance(self.inventory_state, CitrusInventoryState):
            raise TypeError("inventory_state must be a CitrusInventoryState")
        if not isinstance(self.selection_scope, CitrusCandidateScope):
            raise TypeError("selection_scope must be a CitrusCandidateScope")
        if self.exact_stock_ref is not None:
            object.__setattr__(
                self,
                "exact_stock_ref",
                _text(self.exact_stock_ref, "exact_stock_ref"),
            )
        if (
            self.inventory_state is CitrusInventoryState.OWNED
            and self.exact_stock_ref is None
        ):
            raise ValueError("OWNED citrus requires exact_stock_ref")
        object.__setattr__(
            self,
            "transition_to_heart",
            _text(self.transition_to_heart, "transition_to_heart"),
        )
        evidence = _unique_text(self.evidence_refs, "evidence_refs")
        if not evidence:
            raise ValueError("evidence_refs must not be empty")
        object.__setattr__(self, "evidence_refs", evidence)

    def as_dict(self) -> dict[str, Any]:
        return {
            "material": self.material,
            "roles": list(self.roles),
            "axis_matches": list(self.axis_matches),
            "axis_conflicts": list(self.axis_conflicts),
            "inventory_state": self.inventory_state.value,
            "exact_stock_ref": self.exact_stock_ref,
            "transition_to_heart": self.transition_to_heart,
            "evidence_refs": list(self.evidence_refs),
            "selection_scope": self.selection_scope.value,
        }


@dataclass(frozen=True, slots=True)
class CitrusSelectionRequest:
    target_identity: str
    target_axes: tuple[str, ...]
    primary_role: str
    support_role: str | None
    candidates: tuple[CitrusCandidate, ...]
    citrus_required: bool
    non_citrus_brightness_satisfies_target: bool
    inventory_authority_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "target_identity", _text(self.target_identity, "target_identity")
        )
        axes = _unique_text(self.target_axes, "target_axes")
        if len(axes) != 5:
            raise ValueError("target_axes must contain exactly five target axes")
        object.__setattr__(self, "target_axes", axes)
        object.__setattr__(self, "primary_role", _text(self.primary_role, "primary_role"))
        if self.support_role is not None:
            object.__setattr__(
                self, "support_role", _text(self.support_role, "support_role")
            )
        if not isinstance(self.candidates, tuple) or any(
            not isinstance(item, CitrusCandidate) for item in self.candidates
        ):
            raise TypeError("candidates must be a tuple of CitrusCandidate values")
        if not self.candidates:
            raise ValueError("candidates must not be empty")
        materials = tuple(item.material for item in self.candidates)
        if len(materials) != len(set(materials)):
            raise ValueError("candidate materials must be unique")
        for field_name in (
            "citrus_required",
            "non_citrus_brightness_satisfies_target",
        ):
            if not isinstance(getattr(self, field_name), bool):
                raise TypeError(f"{field_name} must be boolean")
        if not isinstance(self.inventory_authority_sha256, str) or _SHA256_RE.fullmatch(
            self.inventory_authority_sha256
        ) is None:
            raise ValueError(
                "inventory_authority_sha256 must be a lowercase SHA-256 digest"
            )

    def with_target_axes(self, target_axes: tuple[str, ...]) -> CitrusSelectionRequest:
        return replace(self, target_axes=target_axes)

    def as_dict(self) -> dict[str, Any]:
        return {
            "target_identity": self.target_identity,
            "target_axes": list(self.target_axes),
            "primary_role": self.primary_role,
            "support_role": self.support_role,
            "candidates": [item.as_dict() for item in self.candidates],
            "citrus_required": self.citrus_required,
            "non_citrus_brightness_satisfies_target": (
                self.non_citrus_brightness_satisfies_target
            ),
            "inventory_authority_sha256": self.inventory_authority_sha256,
        }


@dataclass(frozen=True, slots=True)
class CitrusSelectionResult:
    state: CitrusSelectionState
    target_identity: str
    target_axes: tuple[str, ...]
    primary_role: str
    support_role: str | None
    target_primary: str | None
    target_support: str | None
    current_build_primary: str | None
    current_build_support: str | None
    current_build_primary_stock_ref: str | None
    current_build_support_stock_ref: str | None
    current_build_state: str
    primary_transition_to_heart: str | None
    issue_codes: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    inventory_authority_sha256: str
    claim_ceiling: str = field(default="COMPUTATIONAL_DESIGN_ONLY", init=False)

    def as_dict(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": "citrus_architecture_selection_v1",
            "state": self.state.value,
            "target_identity": self.target_identity,
            "target_axes": list(self.target_axes),
            "primary_role": self.primary_role,
            "support_role": self.support_role,
            "target_ideal": {
                "primary": self.target_primary,
                "support": self.target_support,
                "transition_to_heart": self.primary_transition_to_heart,
            },
            "current_inventory_build": {
                "primary": self.current_build_primary,
                "support": self.current_build_support,
                "primary_stock_ref": self.current_build_primary_stock_ref,
                "support_stock_ref": self.current_build_support_stock_ref,
                "state": self.current_build_state,
            },
            "issue_codes": list(self.issue_codes),
            "evidence_refs": list(self.evidence_refs),
            "inventory_authority_sha256": self.inventory_authority_sha256,
            "claim_ceiling": self.claim_ceiling,
            "formula_authority": False,
            "inventory_authority": False,
            "physical_execution_authorized": False,
            "sensory_authority": False,
            "safety_authority": False,
            "release_authority": False,
        }
        if include_hash:
            payload["result_sha256"] = stable_json_hash(payload)
        return payload

    @property
    def result_sha256(self) -> str:
        return stable_json_hash(self.as_dict(include_hash=False))


def _hold_result(
    request: CitrusSelectionRequest, *issue_codes: str
) -> CitrusSelectionResult:
    return CitrusSelectionResult(
        state=CitrusSelectionState.HOLD,
        target_identity=request.target_identity,
        target_axes=request.target_axes,
        primary_role=request.primary_role,
        support_role=request.support_role,
        target_primary=None,
        target_support=None,
        current_build_primary=None,
        current_build_support=None,
        current_build_primary_stock_ref=None,
        current_build_support_stock_ref=None,
        current_build_state="HOLD_NO_TARGET_SELECTION",
        primary_transition_to_heart=None,
        issue_codes=tuple(issue_codes),
        evidence_refs=(),
        inventory_authority_sha256=request.inventory_authority_sha256,
    )


def _inventory_projection(
    candidate: CitrusCandidate,
) -> tuple[str | None, str | None, str]:
    if (
        candidate.inventory_state is CitrusInventoryState.OWNED
        and candidate.exact_stock_ref is not None
    ):
        return candidate.material, candidate.exact_stock_ref, "BUILD_IDENTIFIED"
    if candidate.inventory_state is CitrusInventoryState.VERIFY_FIRST:
        return None, None, "HOLD_VERIFY_EXACT_STOCK"
    return None, None, "HOLD_TARGET_SPECIFIC_GAP"


def select_citrus_architecture(
    request: CitrusSelectionRequest,
) -> CitrusSelectionResult:
    """Select a target citrus architecture without scalar optimization."""

    if not isinstance(request, CitrusSelectionRequest):
        raise TypeError("request must be a CitrusSelectionRequest")
    if not request.citrus_required:
        issue = (
            "NON_CITRUS_BRIGHTNESS_SUFFICIENT"
            if request.non_citrus_brightness_satisfies_target
            else "CITRUS_NOT_REQUIRED_BY_TARGET"
        )
        return CitrusSelectionResult(
            state=CitrusSelectionState.NONE,
            target_identity=request.target_identity,
            target_axes=request.target_axes,
            primary_role=request.primary_role,
            support_role=request.support_role,
            target_primary=None,
            target_support=None,
            current_build_primary=None,
            current_build_support=None,
            current_build_primary_stock_ref=None,
            current_build_support_stock_ref=None,
            current_build_state="NONE_REQUIRED",
            primary_transition_to_heart=None,
            issue_codes=(issue,),
            evidence_refs=(),
            inventory_authority_sha256=request.inventory_authority_sha256,
        )

    required_axes = set(request.target_axes)
    primary_candidates = tuple(
        item
        for item in request.candidates
        if request.primary_role in item.roles
        and item.selection_scope is CitrusCandidateScope.PRIMARY_OR_SUPPORT
        and not item.axis_conflicts
        and required_axes.issubset(item.axis_matches)
    )
    if not primary_candidates:
        return _hold_result(request, "NO_TARGET_FIT_PRIMARY")
    if len(primary_candidates) > 1:
        return _hold_result(request, "STRONGEST_SINGLE_UNRESOLVED")
    primary = primary_candidates[0]

    support: CitrusCandidate | None = None
    issues: list[str] = []
    if request.support_role is not None:
        if request.support_role in primary.roles:
            issues.append("SUPPORT_NOT_DISTINCT")
        else:
            support_candidates = tuple(
                item
                for item in request.candidates
                if item.material != primary.material
                and request.support_role in item.roles
                and not item.axis_conflicts
                and set(item.roles).isdisjoint(primary.roles)
            )
            if len(support_candidates) == 1:
                support = support_candidates[0]
            elif len(support_candidates) > 1:
                issues.append("SUPPORT_STRONGEST_SINGLE_UNRESOLVED")
            else:
                issues.append("SUPPORT_NOT_JUSTIFIED")

    current_primary, current_primary_stock_ref, build_state = _inventory_projection(
        primary
    )
    if current_primary is None:
        if primary.inventory_state is CitrusInventoryState.OUT_OF_STOCK:
            issues.append("TARGET_PRIMARY_OUT_OF_STOCK")
        elif primary.inventory_state is CitrusInventoryState.VERIFY_FIRST:
            issues.append("TARGET_PRIMARY_VERIFY_FIRST")
        else:
            issues.append("TARGET_PRIMARY_NOT_BUILDABLE")
    current_support: str | None = None
    current_support_stock_ref: str | None = None
    if support is not None:
        current_support, current_support_stock_ref, support_state = (
            _inventory_projection(support)
        )
        if current_support is None:
            issues.append("TARGET_SUPPORT_NOT_BUILDABLE")
            if build_state == "BUILD_IDENTIFIED":
                build_state = support_state

    evidence_refs = tuple(
        dict.fromkeys(
            (*primary.evidence_refs, *(support.evidence_refs if support else ()))
        )
    )
    return CitrusSelectionResult(
        state=CitrusSelectionState.PASS,
        target_identity=request.target_identity,
        target_axes=request.target_axes,
        primary_role=request.primary_role,
        support_role=request.support_role,
        target_primary=primary.material,
        target_support=support.material if support else None,
        current_build_primary=current_primary,
        current_build_support=current_support,
        current_build_primary_stock_ref=current_primary_stock_ref,
        current_build_support_stock_ref=current_support_stock_ref,
        current_build_state=build_state,
        primary_transition_to_heart=primary.transition_to_heart,
        issue_codes=tuple(issues),
        evidence_refs=evidence_refs,
        inventory_authority_sha256=request.inventory_authority_sha256,
    )


__all__ = [
    "CitrusCandidate",
    "CitrusCandidateScope",
    "CitrusInventoryState",
    "CitrusSelectionRequest",
    "CitrusSelectionResult",
    "CitrusSelectionState",
    "select_citrus_architecture",
]
