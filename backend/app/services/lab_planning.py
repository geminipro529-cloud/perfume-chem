"""Immutable command contracts and service operations for A2 planning."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import isclose, isfinite
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from engine.calibration.hashing import stable_json_hash

from app.models.lab import LabEvidenceRecord, LabInventoryMovement, LabStockSolution
from app.models.lab_planning import (
    UNAVAILABLE_INVENTORY_STATUSES,
    LabAcceptedTargetVersion,
    LabBuildPlanEvidenceLink,
    LabBuildPlanLine,
    LabBuildPlanVersion,
    LabFormulaVersionEdge,
    LabInventoryMappingEvidenceLink,
    LabInventoryMappingVersion,
    LabInventoryReservationEvent,
    LabTargetEvidenceLink,
    LabTargetHypothesisVersion,
    LabTargetLine,
)

if TYPE_CHECKING:
    from contextlib import AbstractAsyncContextManager

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.repositories.lab import LabRepository

BUILD_PLAN_TRANSITIONS = {
    "DRAFT": {"UNDER_REVIEW", "CANCELLED", "SUPERSEDED"},
    "UNDER_REVIEW": {"APPROVED", "DRAFT", "CANCELLED", "SUPERSEDED"},
    "APPROVED": {"RESERVED", "CANCELLED", "SUPERSEDED"},
    "RESERVED": {"EXECUTING", "CANCELLED", "SUPERSEDED"},
    "EXECUTING": {"CLOSED", "CANCELLED"},
    "CLOSED": set(),
    "SUPERSEDED": set(),
    "CANCELLED": set(),
}
RESERVATION_TRANSITIONS = {
    "RESERVED": {"RELEASED", "FULFILLED", "CANCELLED"},
    "RELEASED": set(),
    "FULFILLED": set(),
    "CANCELLED": set(),
}


class PlanningDomainError(ValueError):
    """Base class for a stable planning-domain rejection."""

    code = "PLANNING_ERROR"


class PlanningConflictError(PlanningDomainError):
    """A valid command shape that conflicts with canonical state."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class InsufficientAvailableStockError(PlanningConflictError):
    """A reservation would make canonical available stock negative."""

    def __init__(self, available_mass_g: float, requested_mass_g: float) -> None:
        super().__init__(
            "INSUFFICIENT_AVAILABLE_STOCK",
            "Reservation exceeds available stock "
            f"({requested_mass_g:g} g requested, {available_mass_g:g} g available).",
        )


def _text(value: str, field: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise PlanningDomainError(f"{field} must not be blank")
    return normalized


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _finite(value: float, field: str) -> float:
    normalized = float(value)
    if not isfinite(normalized):
        raise PlanningDomainError(f"{field} must be finite")
    return normalized


def _text_tuple(values: tuple[str, ...], field: str) -> tuple[str, ...]:
    normalized = tuple(_text(value, field) for value in values)
    if len(normalized) != len(set(normalized)):
        raise PlanningDomainError(f"{field} must not contain duplicates")
    return normalized


def _identity(value: str) -> str:
    return " ".join(str(value).strip().casefold().split())


@dataclass(frozen=True, slots=True)
class TargetLineInput:
    line_id: str
    target_identity: str
    source_name: str
    grade: str
    presence_probability: float
    target_raw_quantity: float
    target_active_quantity: float
    unit: str
    concentration_fraction: float
    concentration_basis: str
    functional_roles: tuple[str, ...]
    evidence_links: tuple[str, ...]
    uncertainty: dict

    def __post_init__(self) -> None:
        object.__setattr__(self, "line_id", _text(self.line_id, "line_id"))
        object.__setattr__(
            self,
            "target_identity",
            _text(self.target_identity, "target_identity"),
        )
        object.__setattr__(
            self,
            "source_name",
            _text(self.source_name, "source_name"),
        )
        object.__setattr__(self, "grade", _text(self.grade, "grade"))
        probability = _finite(
            self.presence_probability,
            "presence_probability",
        )
        raw = _finite(self.target_raw_quantity, "target_raw_quantity")
        active = _finite(
            self.target_active_quantity,
            "target_active_quantity",
        )
        fraction = _finite(
            self.concentration_fraction,
            "concentration_fraction",
        )
        if not 0 <= probability <= 1:
            raise PlanningDomainError(
                "presence_probability must be between zero and one"
            )
        if raw < 0 or active < 0:
            raise PlanningDomainError("target quantities must be nonnegative")
        if not 0 <= fraction <= 1:
            raise PlanningDomainError(
                "concentration_fraction must be between zero and one"
            )
        if not isclose(active, raw * fraction, rel_tol=1e-9, abs_tol=1e-12):
            raise PlanningDomainError(
                "target active quantity must equal raw quantity times fraction"
            )
        object.__setattr__(self, "presence_probability", probability)
        object.__setattr__(self, "target_raw_quantity", raw)
        object.__setattr__(self, "target_active_quantity", active)
        object.__setattr__(self, "concentration_fraction", fraction)
        object.__setattr__(self, "unit", _text(self.unit, "unit"))
        object.__setattr__(
            self,
            "concentration_basis",
            _text(self.concentration_basis, "concentration_basis"),
        )
        object.__setattr__(
            self,
            "functional_roles",
            _text_tuple(self.functional_roles, "functional_roles"),
        )
        evidence = _text_tuple(self.evidence_links, "evidence_links")
        if not evidence:
            raise PlanningDomainError("evidence_links must not be empty")
        object.__setattr__(self, "evidence_links", evidence)
        object.__setattr__(self, "uncertainty", dict(self.uncertainty))


@dataclass(frozen=True, slots=True)
class TargetHypothesisInput:
    product_key: str
    schema_version: str
    author: str
    provenance_activity: dict
    uncertainty_summary: dict
    rationale: str
    lines: tuple[TargetLineInput, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "product_key",
            _text(self.product_key, "product_key"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _text(self.schema_version, "schema_version"),
        )
        object.__setattr__(self, "author", _text(self.author, "author"))
        object.__setattr__(
            self,
            "rationale",
            _text(self.rationale, "rationale"),
        )
        object.__setattr__(
            self,
            "provenance_activity",
            dict(self.provenance_activity),
        )
        object.__setattr__(
            self,
            "uncertainty_summary",
            dict(self.uncertainty_summary),
        )
        lines = tuple(self.lines)
        if not lines:
            raise PlanningDomainError("target hypothesis requires at least one line")
        line_ids = [line.line_id for line in lines]
        if len(line_ids) != len(set(line_ids)):
            raise PlanningDomainError("target line IDs must be unique")
        object.__setattr__(self, "lines", lines)


@dataclass(frozen=True, slots=True)
class InventoryMappingInput:
    target_line_id: str
    stock_solution_id: str | None
    target_identity: str
    build_identity: str
    identity_status: str
    inventory_status: str
    substitution_class: str
    preserved_functions: tuple[str, ...]
    lost_functions: tuple[str, ...]
    confidence: float
    rationale: str
    evidence_links: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "target_line_id",
            _text(self.target_line_id, "target_line_id"),
        )
        stock_id = _optional_text(self.stock_solution_id)
        inventory_status = _text(self.inventory_status, "inventory_status")
        unavailable = inventory_status in UNAVAILABLE_INVENTORY_STATUSES
        if (stock_id is None) != unavailable:
            raise PlanningDomainError(
                "stock_solution_id must be omitted only for an unavailable status"
            )
        confidence = _finite(self.confidence, "confidence")
        if not 0 <= confidence <= 1:
            raise PlanningDomainError("confidence must be between zero and one")
        object.__setattr__(self, "stock_solution_id", stock_id)
        object.__setattr__(
            self,
            "target_identity",
            _text(self.target_identity, "target_identity"),
        )
        object.__setattr__(
            self,
            "build_identity",
            _text(self.build_identity, "build_identity"),
        )
        object.__setattr__(
            self,
            "identity_status",
            _text(self.identity_status, "identity_status"),
        )
        object.__setattr__(self, "inventory_status", inventory_status)
        object.__setattr__(
            self,
            "substitution_class",
            _text(self.substitution_class, "substitution_class"),
        )
        object.__setattr__(
            self,
            "preserved_functions",
            _text_tuple(self.preserved_functions, "preserved_functions"),
        )
        object.__setattr__(
            self,
            "lost_functions",
            _text_tuple(self.lost_functions, "lost_functions"),
        )
        object.__setattr__(self, "confidence", confidence)
        object.__setattr__(
            self,
            "rationale",
            _text(self.rationale, "rationale"),
        )
        evidence = _text_tuple(self.evidence_links, "evidence_links")
        if not evidence:
            raise PlanningDomainError("evidence_links must not be empty")
        object.__setattr__(self, "evidence_links", evidence)


@dataclass(frozen=True, slots=True)
class BuildPlanLineInput:
    line_id: str
    target_line_id: str
    target_identity: str
    inventory_mapping_version_id: str
    stock_solution_id: str
    planned_raw_quantity: float
    planned_active_quantity: float
    unit: str
    concentration_fraction: float
    concentration_basis: str
    density_g_ml: float | None
    density_source: str | None
    standard_uncertainty: float | None
    measurement_method: str
    resolution: float
    expected_transfer_loss: float
    substitution_class: str
    preserved_functions: tuple[str, ...]
    lost_functions: tuple[str, ...]
    rationale: str
    evidence_links: tuple[str, ...]

    def __post_init__(self) -> None:
        for field in (
            "line_id",
            "target_line_id",
            "target_identity",
            "inventory_mapping_version_id",
            "stock_solution_id",
            "unit",
            "concentration_basis",
            "measurement_method",
            "substitution_class",
            "rationale",
        ):
            object.__setattr__(
                self,
                field,
                _text(getattr(self, field), field),
            )
        raw = _finite(self.planned_raw_quantity, "planned_raw_quantity")
        active = _finite(
            self.planned_active_quantity,
            "planned_active_quantity",
        )
        fraction = _finite(
            self.concentration_fraction,
            "concentration_fraction",
        )
        resolution = _finite(self.resolution, "resolution")
        loss = _finite(
            self.expected_transfer_loss,
            "expected_transfer_loss",
        )
        if raw < 0 or active < 0:
            raise PlanningDomainError("planned quantities must be nonnegative")
        if not 0 <= fraction <= 1:
            raise PlanningDomainError(
                "concentration_fraction must be between zero and one"
            )
        if not isclose(active, raw * fraction, rel_tol=1e-9, abs_tol=1e-12):
            raise PlanningDomainError(
                "planned active quantity must equal raw quantity times fraction"
            )
        if resolution <= 0:
            raise PlanningDomainError("resolution must be greater than zero")
        if loss < 0:
            raise PlanningDomainError(
                "expected_transfer_loss must be nonnegative"
            )
        density = (
            _finite(self.density_g_ml, "density_g_ml")
            if self.density_g_ml is not None
            else None
        )
        if density is not None and density <= 0:
            raise PlanningDomainError("density_g_ml must be greater than zero")
        uncertainty = (
            _finite(self.standard_uncertainty, "standard_uncertainty")
            if self.standard_uncertainty is not None
            else None
        )
        if uncertainty is not None and uncertainty < 0:
            raise PlanningDomainError(
                "standard_uncertainty must be nonnegative"
            )
        object.__setattr__(self, "planned_raw_quantity", raw)
        object.__setattr__(self, "planned_active_quantity", active)
        object.__setattr__(self, "concentration_fraction", fraction)
        object.__setattr__(self, "resolution", resolution)
        object.__setattr__(self, "expected_transfer_loss", loss)
        object.__setattr__(self, "density_g_ml", density)
        object.__setattr__(
            self,
            "density_source",
            _optional_text(self.density_source),
        )
        object.__setattr__(self, "standard_uncertainty", uncertainty)
        object.__setattr__(
            self,
            "preserved_functions",
            _text_tuple(self.preserved_functions, "preserved_functions"),
        )
        object.__setattr__(
            self,
            "lost_functions",
            _text_tuple(self.lost_functions, "lost_functions"),
        )
        evidence = _text_tuple(self.evidence_links, "evidence_links")
        if not evidence:
            raise PlanningDomainError("evidence_links must not be empty")
        object.__setattr__(self, "evidence_links", evidence)


@dataclass(frozen=True, slots=True)
class BuildPlanInput:
    target_hypothesis_version_id: str
    accepted_target_version_id: str
    schema_version: str
    author: str
    inventory_snapshot_ref: str
    uncertainty_summary: dict
    rationale: str
    lines: tuple[BuildPlanLineInput, ...]

    def __post_init__(self) -> None:
        for field in (
            "target_hypothesis_version_id",
            "accepted_target_version_id",
            "schema_version",
            "author",
            "inventory_snapshot_ref",
            "rationale",
        ):
            object.__setattr__(
                self,
                field,
                _text(getattr(self, field), field),
            )
        object.__setattr__(
            self,
            "uncertainty_summary",
            dict(self.uncertainty_summary),
        )
        lines = tuple(self.lines)
        if not lines:
            raise PlanningDomainError("build plan requires at least one line")
        line_ids = [line.line_id for line in lines]
        target_line_ids = [line.target_line_id for line in lines]
        if len(line_ids) != len(set(line_ids)):
            raise PlanningDomainError("build plan line IDs must be unique")
        if len(target_line_ids) != len(set(target_line_ids)):
            raise PlanningDomainError(
                "build plan target line IDs must be unique"
            )
        object.__setattr__(self, "lines", lines)


def _target_payload(
    *,
    target_id: str,
    version_number: int,
    parent_sha256: str | None,
    command: TargetHypothesisInput,
) -> dict[str, Any]:
    return {
        "schema": "a2-target-hypothesis-v1",
        "target_id": target_id,
        "version_number": version_number,
        "parent_sha256": parent_sha256,
        "product_key": command.product_key,
        "schema_version": command.schema_version,
        "author": command.author,
        "provenance_activity": command.provenance_activity,
        "uncertainty_summary": command.uncertainty_summary,
        "rationale": command.rationale,
        "lines": [
            {
                "position": position,
                "line_id": line.line_id,
                "target_identity": line.target_identity,
                "source_name": line.source_name,
                "grade": line.grade,
                "presence_probability": line.presence_probability,
                "target_raw_quantity": line.target_raw_quantity,
                "target_active_quantity": line.target_active_quantity,
                "unit": line.unit,
                "concentration_fraction": line.concentration_fraction,
                "concentration_basis": line.concentration_basis,
                "functional_roles": line.functional_roles,
                "evidence_links": line.evidence_links,
                "uncertainty": line.uncertainty,
            }
            for position, line in enumerate(command.lines, start=1)
        ],
    }


def _mapping_payload(
    *,
    mapping_id: str,
    version_number: int,
    parent_sha256: str | None,
    command: InventoryMappingInput,
) -> dict[str, Any]:
    return {
        "schema": "a2-inventory-mapping-v1",
        "mapping_id": mapping_id,
        "version_number": version_number,
        "parent_sha256": parent_sha256,
        "target_line_id": command.target_line_id,
        "stock_solution_id": command.stock_solution_id,
        "target_identity": command.target_identity,
        "build_identity": command.build_identity,
        "identity_status": command.identity_status,
        "inventory_status": command.inventory_status,
        "substitution_class": command.substitution_class,
        "preserved_functions": command.preserved_functions,
        "lost_functions": command.lost_functions,
        "confidence": command.confidence,
        "rationale": command.rationale,
        "evidence_links": command.evidence_links,
    }


def _build_line_payload(line: BuildPlanLineInput) -> dict[str, Any]:
    return {
        "line_id": line.line_id,
        "target_line_id": line.target_line_id,
        "target_identity": line.target_identity,
        "inventory_mapping_version_id": line.inventory_mapping_version_id,
        "stock_solution_id": line.stock_solution_id,
        "planned_raw_quantity": line.planned_raw_quantity,
        "planned_active_quantity": line.planned_active_quantity,
        "unit": line.unit,
        "concentration_fraction": line.concentration_fraction,
        "concentration_basis": line.concentration_basis,
        "density_g_ml": line.density_g_ml,
        "density_source": line.density_source,
        "standard_uncertainty": line.standard_uncertainty,
        "measurement_method": line.measurement_method,
        "resolution": line.resolution,
        "expected_transfer_loss": line.expected_transfer_loss,
        "substitution_class": line.substitution_class,
        "preserved_functions": line.preserved_functions,
        "lost_functions": line.lost_functions,
        "rationale": line.rationale,
        "evidence_links": line.evidence_links,
    }


class LabPlanningServiceMixin:
    """Planning commands that rely on the canonical service transaction owner."""

    if TYPE_CHECKING:
        repository: LabRepository
        session: AsyncSession

        def _transaction(self) -> AbstractAsyncContextManager[None]: ...

        async def _append_inventory_movement(
            self,
            *,
            stock: LabStockSolution,
            movement_type: str,
            raw_quantity: float,
            balance_before: float,
            balance_after: float,
            actor: str,
            transaction_id: str,
            idempotency_key: str,
            reason: str,
            mass_delta_g: float,
            event_effect_id: str | None = None,
            build_plan_line_id: str | None = None,
            reservation_event_id: str | None = None,
            bottle_event_id: str | None = None,
            admin_cause: str | None = None,
            correction_of_movement_id: str | None = None,
            reversal_of_movement_id: str | None = None,
            measured_volume_ul: float | None = None,
            standard_uncertainty: float | None = None,
        ) -> LabInventoryMovement: ...

    async def _require_evidence_links(
        self,
        evidence_ids: tuple[str, ...],
    ) -> None:
        for evidence_id in evidence_ids:
            if await self.repository.get_evidence_record(evidence_id) is None:
                raise PlanningConflictError(
                    "EVIDENCE_NOT_FOUND",
                    f"Evidence record not found: {evidence_id}.",
                )

    async def record_evidence(
        self,
        *,
        claim_key: str,
        classification: str,
        source_locator: str,
        source_version: str | None,
        method: str | None,
        assumptions: tuple[str, ...],
        limitations: tuple[str, ...],
        payload_sha256: str | None,
    ) -> LabEvidenceRecord:
        claim = _text(claim_key, "claim_key")
        kind = _text(classification, "classification")
        locator = _text(source_locator, "source_locator")
        payload_hash = _optional_text(payload_sha256)
        if payload_hash is not None and (
            len(payload_hash) != 64
            or any(character not in "0123456789abcdefABCDEF" for character in payload_hash)
        ):
            raise PlanningDomainError(
                "payload_sha256 must be a 64-character hexadecimal digest"
            )
        async with self._transaction():
            return await self.repository.add(
                LabEvidenceRecord(
                    claim_key=claim,
                    classification=kind,
                    source_locator=locator,
                    source_version=_optional_text(source_version),
                    method=_optional_text(method),
                    assumptions_json=list(assumptions),
                    limitations_json=list(limitations),
                    payload_sha256=(
                        payload_hash.casefold() if payload_hash is not None else None
                    ),
                )
            )

    async def create_target_hypothesis(
        self,
        command: TargetHypothesisInput,
    ) -> LabTargetHypothesisVersion:
        async with self._transaction():
            return await self._write_target_version(
                target_id=str(uuid4()),
                version_number=1,
                parent=None,
                command=command,
            )

    async def revise_target_hypothesis(
        self,
        parent_version_id: str,
        command: TargetHypothesisInput,
    ) -> LabTargetHypothesisVersion:
        async with self._transaction():
            parent = await self.repository.get_target_version(parent_version_id)
            if parent is None:
                raise PlanningConflictError(
                    "TARGET_NOT_FOUND",
                    f"Target version not found: {parent_version_id}.",
                )
            latest = await self.repository.latest_target_version(parent.target_id)
            if latest is None or latest.id != parent.id:
                raise PlanningConflictError(
                    "STALE_TARGET_VERSION",
                    "Target revisions must use the latest immutable version.",
                )
            return await self._write_target_version(
                target_id=parent.target_id,
                version_number=parent.version_number + 1,
                parent=parent,
                command=command,
            )

    async def _write_target_version(
        self,
        *,
        target_id: str,
        version_number: int,
        parent: LabTargetHypothesisVersion | None,
        command: TargetHypothesisInput,
    ) -> LabTargetHypothesisVersion:
        for line in command.lines:
            await self._require_evidence_links(line.evidence_links)
        parent_sha256 = parent.content_sha256 if parent is not None else None
        version = LabTargetHypothesisVersion(
            target_id=target_id,
            version_number=version_number,
            schema_version=command.schema_version,
            product_key=command.product_key,
            parent_version_id=parent.id if parent is not None else None,
            author=command.author,
            provenance_activity_json=dict(command.provenance_activity),
            uncertainty_summary_json=dict(command.uncertainty_summary),
            rationale=command.rationale,
            content_sha256=stable_json_hash(
                _target_payload(
                    target_id=target_id,
                    version_number=version_number,
                    parent_sha256=parent_sha256,
                    command=command,
                )
            ),
            parent_sha256=parent_sha256,
        )
        await self.repository.add(version)
        for position, line in enumerate(command.lines, start=1):
            target_line = await self.repository.add(
                LabTargetLine(
                    line_id=line.line_id,
                    target_hypothesis_version_id=version.id,
                    position=position,
                    target_identity=line.target_identity,
                    source_name=line.source_name,
                    grade=line.grade,
                    presence_probability=line.presence_probability,
                    target_raw_quantity=line.target_raw_quantity,
                    target_active_quantity=line.target_active_quantity,
                    unit=line.unit,
                    concentration_fraction=line.concentration_fraction,
                    concentration_basis=line.concentration_basis,
                    functional_roles_json=list(line.functional_roles),
                    uncertainty_json=dict(line.uncertainty),
                )
            )
            for evidence_id in line.evidence_links:
                await self.repository.add(
                    LabTargetEvidenceLink(
                        target_hypothesis_version_id=version.id,
                        target_line_id=target_line.id,
                        evidence_record_id=evidence_id,
                    )
                )
        return version

    async def accept_target(
        self,
        target_version_id: str,
        *,
        reviewer: str,
        rationale: str,
    ) -> LabAcceptedTargetVersion:
        reviewer = _text(reviewer, "reviewer")
        rationale = _text(rationale, "rationale")
        async with self._transaction():
            target = await self.repository.get_target_version(target_version_id)
            if target is None:
                raise PlanningConflictError(
                    "TARGET_NOT_FOUND",
                    f"Target version not found: {target_version_id}.",
                )
            if (
                await self.repository.acceptance_for_target_version(
                    target_version_id
                )
                is not None
            ):
                raise PlanningConflictError(
                    "TARGET_ALREADY_ACCEPTED",
                    "Target version already has an immutable acceptance.",
                )
            accepted_target_id = str(uuid4())
            payload = {
                "schema": "a2-accepted-target-v1",
                "accepted_target_id": accepted_target_id,
                "version_number": 1,
                "target_hypothesis_version_id": target.id,
                "target_content_sha256": target.content_sha256,
                "reviewer": reviewer,
                "rationale": rationale,
            }
            return await self.repository.add(
                LabAcceptedTargetVersion(
                    accepted_target_id=accepted_target_id,
                    version_number=1,
                    target_hypothesis_version_id=target.id,
                    reviewer=reviewer,
                    rationale=rationale,
                    content_sha256=stable_json_hash(payload),
                )
            )

    async def link_formula_version(
        self,
        child_version_id: str,
        parent_version_id: str,
        *,
        relationship_kind: str,
        change: dict,
        rationale: str,
    ) -> LabFormulaVersionEdge:
        child_version_id = _text(child_version_id, "child_version_id")
        parent_version_id = _text(parent_version_id, "parent_version_id")
        relationship_kind = _text(relationship_kind, "relationship_kind")
        rationale = _text(rationale, "rationale")
        if child_version_id == parent_version_id:
            raise PlanningConflictError(
                "FORMULA_VERSION_SELF_EDGE",
                "A formula version cannot be its own parent.",
            )
        async with self._transaction():
            for version_id in (child_version_id, parent_version_id):
                if await self.repository.get_formula_version(version_id) is None:
                    raise PlanningConflictError(
                        "FORMULA_VERSION_NOT_FOUND",
                        f"Formula version not found: {version_id}.",
                    )
            if any(
                edge.parent_version_id == parent_version_id
                for edge in await self.repository.formula_parent_edges(
                    child_version_id
                )
            ):
                raise PlanningConflictError(
                    "FORMULA_VERSION_EDGE_EXISTS",
                    "The formula-version lineage edge already exists.",
                )
            if await self.repository.formula_has_path(
                parent_version_id,
                child_version_id,
            ):
                raise PlanningConflictError(
                    "FORMULA_VERSION_CYCLE",
                    "The formula-version lineage edge would create a cycle.",
                )
            payload = {
                "schema": "a2-formula-version-edge-v1",
                "child_version_id": child_version_id,
                "parent_version_id": parent_version_id,
                "relationship_kind": relationship_kind,
                "change": dict(change),
                "rationale": rationale,
            }
            return await self.repository.add(
                LabFormulaVersionEdge(
                    child_version_id=child_version_id,
                    parent_version_id=parent_version_id,
                    relationship_kind=relationship_kind,
                    change_json=dict(change),
                    rationale=rationale,
                    content_sha256=stable_json_hash(payload),
                )
            )

    async def create_inventory_mapping(
        self,
        command: InventoryMappingInput,
    ) -> LabInventoryMappingVersion:
        async with self._transaction():
            return await self._write_mapping_version(
                mapping_id=str(uuid4()),
                version_number=1,
                parent=None,
                command=command,
            )

    async def revise_inventory_mapping(
        self,
        parent_version_id: str,
        command: InventoryMappingInput,
    ) -> LabInventoryMappingVersion:
        async with self._transaction():
            parent = await self.repository.get_mapping_version(parent_version_id)
            if parent is None:
                raise PlanningConflictError(
                    "MAPPING_NOT_FOUND",
                    f"Inventory mapping version not found: {parent_version_id}.",
                )
            latest = await self.repository.latest_mapping_version(
                parent.mapping_id
            )
            if latest is None or latest.id != parent.id:
                raise PlanningConflictError(
                    "STALE_MAPPING_VERSION",
                    "Mapping revisions must use the latest immutable version.",
                )
            if command.target_line_id != parent.target_line_id:
                raise PlanningConflictError(
                    "MAPPING_TARGET_IMMUTABLE",
                    "A mapping revision cannot change its target line.",
                )
            return await self._write_mapping_version(
                mapping_id=parent.mapping_id,
                version_number=parent.version_number + 1,
                parent=parent,
                command=command,
            )

    async def _write_mapping_version(
        self,
        *,
        mapping_id: str,
        version_number: int,
        parent: LabInventoryMappingVersion | None,
        command: InventoryMappingInput,
    ) -> LabInventoryMappingVersion:
        target_line = await self.repository.get_target_line(command.target_line_id)
        if target_line is None:
            raise PlanningConflictError(
                "TARGET_LINE_NOT_FOUND",
                f"Target line not found: {command.target_line_id}.",
            )
        if _identity(command.target_identity) != _identity(
            target_line.target_identity
        ):
            raise PlanningConflictError(
                "MAPPING_TARGET_IDENTITY_MISMATCH",
                "Mapping target identity must match the immutable target line.",
            )
        if command.stock_solution_id is not None:
            stock = await self.repository.get_stock(command.stock_solution_id)
            if stock is None:
                raise PlanningConflictError(
                    "STOCK_SOLUTION_NOT_FOUND",
                    f"Stock solution not found: {command.stock_solution_id}.",
                )
            if command.identity_status == "EXACT":
                material = await self.repository.get_material(stock.material_id)
                if material is None or _identity(
                    material.canonical_name
                ) != _identity(command.build_identity):
                    raise PlanningConflictError(
                        "EXACT_MAPPING_IDENTITY_MISMATCH",
                        "Exact mapping build identity conflicts with the stock material.",
                    )
        await self._require_evidence_links(command.evidence_links)
        parent_sha256 = parent.content_sha256 if parent is not None else None
        mapping = LabInventoryMappingVersion(
            mapping_id=mapping_id,
            version_number=version_number,
            parent_version_id=parent.id if parent is not None else None,
            target_line_id=command.target_line_id,
            stock_solution_id=command.stock_solution_id,
            target_identity=command.target_identity,
            build_identity=command.build_identity,
            identity_status=command.identity_status,
            inventory_status=command.inventory_status,
            substitution_class=command.substitution_class,
            preserved_functions_json=list(command.preserved_functions),
            lost_functions_json=list(command.lost_functions),
            confidence=command.confidence,
            rationale=command.rationale,
            content_sha256=stable_json_hash(
                _mapping_payload(
                    mapping_id=mapping_id,
                    version_number=version_number,
                    parent_sha256=parent_sha256,
                    command=command,
                )
            ),
            parent_sha256=parent_sha256,
        )
        await self.repository.add(mapping)
        for evidence_id in command.evidence_links:
            await self.repository.add(
                LabInventoryMappingEvidenceLink(
                    inventory_mapping_version_id=mapping.id,
                    evidence_record_id=evidence_id,
                )
            )
        return mapping

    async def create_build_plan(
        self,
        command: BuildPlanInput,
    ) -> LabBuildPlanVersion:
        async with self._transaction():
            await self._validate_build_plan_command(command)
            return await self._write_build_plan_version(
                plan_id=str(uuid4()),
                version_number=1,
                parent=None,
                status="DRAFT",
                author=command.author,
                reviewer=None,
                reviewed_at=None,
                command=command,
            )

    async def _validate_build_plan_command(
        self,
        command: BuildPlanInput,
    ) -> None:
        target = await self.repository.get_target_version(
            command.target_hypothesis_version_id
        )
        if target is None:
            raise PlanningConflictError(
                "TARGET_NOT_FOUND",
                "The build plan target version does not exist.",
            )
        acceptance = await self.repository.get_acceptance(
            command.accepted_target_version_id
        )
        if acceptance is None:
            raise PlanningConflictError(
                "ACCEPTANCE_NOT_FOUND",
                "The accepted target version does not exist.",
            )
        if (
            acceptance.target_hypothesis_version_id
            != command.target_hypothesis_version_id
        ):
            raise PlanningConflictError(
                "ACCEPTANCE_TARGET_MISMATCH",
                "The acceptance does not authorize the selected target version.",
            )
        for line in command.lines:
            target_line = await self.repository.get_target_line(
                line.target_line_id
            )
            if target_line is None:
                raise PlanningConflictError(
                    "TARGET_LINE_NOT_FOUND",
                    f"Target line not found: {line.target_line_id}.",
                )
            if (
                target_line.target_hypothesis_version_id
                != command.target_hypothesis_version_id
            ):
                raise PlanningConflictError(
                    "BUILD_LINE_TARGET_MISMATCH",
                    "Build line does not belong to the selected target version.",
                )
            mapping = await self.repository.get_mapping_version(
                line.inventory_mapping_version_id
            )
            if mapping is None:
                raise PlanningConflictError(
                    "MAPPING_NOT_FOUND",
                    f"Mapping version not found: {line.inventory_mapping_version_id}.",
                )
            if (
                mapping.target_line_id != line.target_line_id
                or mapping.stock_solution_id != line.stock_solution_id
            ):
                raise PlanningConflictError(
                    "BUILD_LINE_MAPPING_MISMATCH",
                    "Build line must use the mapping's target line and stock.",
                )
            if await self.repository.get_stock(line.stock_solution_id) is None:
                raise PlanningConflictError(
                    "STOCK_SOLUTION_NOT_FOUND",
                    f"Stock solution not found: {line.stock_solution_id}.",
                )
            await self._require_evidence_links(line.evidence_links)

    async def _write_build_plan_version(
        self,
        *,
        plan_id: str,
        version_number: int,
        parent: LabBuildPlanVersion | None,
        status: str,
        author: str,
        reviewer: str | None,
        reviewed_at: datetime | None,
        command: BuildPlanInput,
    ) -> LabBuildPlanVersion:
        parent_sha256 = parent.content_sha256 if parent is not None else None
        payload = {
            "schema": "a2-build-plan-v1",
            "plan_id": plan_id,
            "version_number": version_number,
            "parent_sha256": parent_sha256,
            "status": status,
            "target_hypothesis_version_id": command.target_hypothesis_version_id,
            "accepted_target_version_id": command.accepted_target_version_id,
            "schema_version": command.schema_version,
            "author": author,
            "reviewer": reviewer,
            "reviewed_at": reviewed_at.isoformat() if reviewed_at else None,
            "inventory_snapshot_ref": command.inventory_snapshot_ref,
            "uncertainty_summary": command.uncertainty_summary,
            "rationale": command.rationale,
            "lines": [
                {
                    "position": position,
                    **_build_line_payload(line),
                }
                for position, line in enumerate(command.lines, start=1)
            ],
        }
        plan = LabBuildPlanVersion(
            plan_id=plan_id,
            version_number=version_number,
            schema_version=command.schema_version,
            target_hypothesis_version_id=command.target_hypothesis_version_id,
            accepted_target_version_id=command.accepted_target_version_id,
            parent_version_id=parent.id if parent is not None else None,
            status=status,
            author=author,
            reviewer=reviewer,
            reviewed_at=reviewed_at,
            provenance_activity_json={
                "activity": "build-plan-transition" if parent else "build-plan-create"
            },
            inventory_snapshot_ref=command.inventory_snapshot_ref,
            content_sha256=stable_json_hash(payload),
            parent_sha256=parent_sha256,
            uncertainty_summary_json=dict(command.uncertainty_summary),
            rationale=command.rationale,
        )
        await self.repository.add(plan)
        for position, line in enumerate(command.lines, start=1):
            plan_line = await self.repository.add(
                LabBuildPlanLine(
                    line_id=line.line_id,
                    build_plan_version_id=plan.id,
                    position=position,
                    target_line_id=line.target_line_id,
                    target_identity=line.target_identity,
                    inventory_mapping_version_id=line.inventory_mapping_version_id,
                    stock_solution_id=line.stock_solution_id,
                    planned_raw_quantity=line.planned_raw_quantity,
                    planned_active_quantity=line.planned_active_quantity,
                    unit=line.unit,
                    concentration_fraction=line.concentration_fraction,
                    concentration_basis=line.concentration_basis,
                    density_g_ml=line.density_g_ml,
                    density_source=line.density_source,
                    standard_uncertainty=line.standard_uncertainty,
                    measurement_method=line.measurement_method,
                    resolution=line.resolution,
                    expected_transfer_loss=line.expected_transfer_loss,
                    substitution_class=line.substitution_class,
                    preserved_functions_json=list(line.preserved_functions),
                    lost_functions_json=list(line.lost_functions),
                    rationale=line.rationale,
                    reservation_state=(
                        "RESERVED" if status == "RESERVED" else "UNRESERVED"
                    ),
                    execution_state="PLANNED",
                )
            )
            for evidence_id in line.evidence_links:
                await self.repository.add(
                    LabBuildPlanEvidenceLink(
                        build_plan_version_id=plan.id,
                        build_plan_line_id=plan_line.id,
                        evidence_record_id=evidence_id,
                    )
                )
        return plan

    async def _build_plan_command_from_version(
        self,
        current: LabBuildPlanVersion,
        *,
        rationale: str,
    ) -> BuildPlanInput:
        existing_lines = await self.repository.build_plan_lines(current.id)
        evidence_by_line: dict[str, tuple[str, ...]] = {}
        for line in existing_lines:
            links = await self.session.execute(
                LabBuildPlanEvidenceLink.__table__.select()
                .with_only_columns(
                    LabBuildPlanEvidenceLink.evidence_record_id
                )
                .where(LabBuildPlanEvidenceLink.build_plan_line_id == line.id)
                .order_by(LabBuildPlanEvidenceLink.evidence_record_id)
            )
            evidence_by_line[line.id] = tuple(links.scalars())
        return BuildPlanInput(
            target_hypothesis_version_id=current.target_hypothesis_version_id,
            accepted_target_version_id=current.accepted_target_version_id,
            schema_version=current.schema_version,
            author=current.author,
            inventory_snapshot_ref=current.inventory_snapshot_ref,
            uncertainty_summary=dict(current.uncertainty_summary_json),
            rationale=rationale,
            lines=tuple(
                BuildPlanLineInput(
                    line_id=line.line_id,
                    target_line_id=line.target_line_id,
                    target_identity=line.target_identity,
                    inventory_mapping_version_id=line.inventory_mapping_version_id,
                    stock_solution_id=line.stock_solution_id,
                    planned_raw_quantity=line.planned_raw_quantity,
                    planned_active_quantity=line.planned_active_quantity,
                    unit=line.unit,
                    concentration_fraction=line.concentration_fraction,
                    concentration_basis=line.concentration_basis,
                    density_g_ml=line.density_g_ml,
                    density_source=line.density_source,
                    standard_uncertainty=line.standard_uncertainty,
                    measurement_method=line.measurement_method,
                    resolution=line.resolution,
                    expected_transfer_loss=line.expected_transfer_loss,
                    substitution_class=line.substitution_class,
                    preserved_functions=tuple(
                        line.preserved_functions_json
                    ),
                    lost_functions=tuple(line.lost_functions_json),
                    rationale=line.rationale,
                    evidence_links=evidence_by_line[line.id],
                )
                for line in existing_lines
            ),
        )

    async def transition_build_plan(
        self,
        version_id: str,
        *,
        next_status: str,
        actor: str,
        rationale: str,
    ) -> LabBuildPlanVersion:
        next_status = _text(next_status, "next_status")
        actor = _text(actor, "actor")
        rationale = _text(rationale, "rationale")
        async with self._transaction():
            current = await self.repository.get_build_plan_version(version_id)
            if current is None:
                raise PlanningConflictError(
                    "BUILD_PLAN_NOT_FOUND",
                    f"Build plan version not found: {version_id}.",
                )
            latest = await self.repository.latest_build_plan_version(
                current.plan_id
            )
            if latest is None or latest.id != current.id:
                raise PlanningConflictError(
                    "STALE_BUILD_PLAN_VERSION",
                    "Build-plan transitions must use the latest immutable version.",
                )
            if next_status not in BUILD_PLAN_TRANSITIONS.get(
                current.status,
                set(),
            ):
                raise PlanningConflictError(
                    "INVALID_BUILD_PLAN_TRANSITION",
                    f"Build plan cannot transition from {current.status} "
                    f"to {next_status}.",
                )
            command = await self._build_plan_command_from_version(
                current,
                rationale=rationale,
            )
            reviewed_at = (
                datetime.now(timezone.utc)
                if next_status == "APPROVED"
                else current.reviewed_at
            )
            reviewer = actor if next_status == "APPROVED" else current.reviewer
            return await self._write_build_plan_version(
                plan_id=current.plan_id,
                version_number=current.version_number + 1,
                parent=current,
                status=next_status,
                author=current.author,
                reviewer=reviewer,
                reviewed_at=reviewed_at,
                command=command,
            )

    async def available_stock_g(self, stock_solution_id: str) -> float:
        stock_solution_id = _text(
            stock_solution_id,
            "stock_solution_id",
        )
        if await self.repository.get_stock(stock_solution_id) is None:
            raise PlanningConflictError(
                "STOCK_SOLUTION_NOT_FOUND",
                f"Stock solution not found: {stock_solution_id}.",
            )
        canonical_balance = await self.repository.stock_balance_g(
            stock_solution_id
        )
        reserved = await self.repository.active_reserved_mass_g(
            stock_solution_id
        )
        return canonical_balance - reserved

    async def reserve_inventory(
        self,
        *,
        build_plan_version_id: str,
        build_plan_line_id: str,
        stock_solution_id: str,
        reserved_mass_g: float,
        idempotency_key: str,
        actor: str,
        rationale: str,
    ) -> LabInventoryReservationEvent:
        build_plan_version_id = _text(
            build_plan_version_id,
            "build_plan_version_id",
        )
        build_plan_line_id = _text(
            build_plan_line_id,
            "build_plan_line_id",
        )
        stock_solution_id = _text(
            stock_solution_id,
            "stock_solution_id",
        )
        idempotency_key = _text(idempotency_key, "idempotency_key")
        actor = _text(actor, "actor")
        rationale = _text(rationale, "rationale")
        mass = _finite(reserved_mass_g, "reserved_mass_g")
        if mass <= 0:
            raise PlanningDomainError(
                "reserved_mass_g must be greater than zero"
            )
        command_payload = {
            "schema": "a2-reservation-command-v1",
            "operation": "RESERVE",
            "build_plan_version_id": build_plan_version_id,
            "build_plan_line_id": build_plan_line_id,
            "stock_solution_id": stock_solution_id,
            "reserved_mass_g": mass,
            "idempotency_key": idempotency_key,
            "actor": actor,
            "rationale": rationale,
        }
        command_sha256 = stable_json_hash(command_payload)
        async with self._transaction():
            existing = (
                await self.repository.reservation_event_for_idempotency(
                    idempotency_key
                )
            )
            if existing is not None:
                if existing.command_sha256 == command_sha256:
                    return existing
                raise PlanningConflictError(
                    "RESERVATION_IDEMPOTENCY_CONFLICT",
                    "Reservation idempotency key was reused for a different command.",
                )
            plan = await self.repository.get_build_plan_version(
                build_plan_version_id
            )
            if plan is None:
                raise PlanningConflictError(
                    "BUILD_PLAN_NOT_FOUND",
                    f"Build plan version not found: {build_plan_version_id}.",
                )
            if plan.status != "APPROVED":
                raise PlanningConflictError(
                    "BUILD_PLAN_NOT_APPROVED",
                    "Inventory may be reserved only for an approved build plan.",
                )
            latest_plan = await self.repository.latest_build_plan_version(
                plan.plan_id
            )
            if latest_plan is None or latest_plan.id != plan.id:
                raise PlanningConflictError(
                    "STALE_BUILD_PLAN_VERSION",
                    "Reservations must use the latest immutable build-plan version.",
                )
            line = await self.repository.get_build_plan_line(
                build_plan_line_id
            )
            if line is None:
                raise PlanningConflictError(
                    "BUILD_PLAN_LINE_NOT_FOUND",
                    f"Build plan line not found: {build_plan_line_id}.",
                )
            if line.build_plan_version_id != plan.id:
                raise PlanningConflictError(
                    "BUILD_PLAN_LINE_MISMATCH",
                    "Build plan line does not belong to the selected plan version.",
                )
            stock = await self.repository.get_stock(stock_solution_id)
            if stock is None:
                raise PlanningConflictError(
                    "STOCK_SOLUTION_NOT_FOUND",
                    f"Stock solution not found: {stock_solution_id}.",
                )
            if line.stock_solution_id != stock_solution_id:
                raise PlanningConflictError(
                    "RESERVATION_STOCK_MISMATCH",
                    "Reservation stock must match the immutable build-plan line.",
                )
            active_line_ids = (
                await self.repository.active_reserved_build_line_ids(plan.id)
            )
            if line.id in active_line_ids:
                raise PlanningConflictError(
                    "BUILD_PLAN_LINE_ALREADY_RESERVED",
                    "Build plan line already has an active reservation.",
                )
            available = await self.available_stock_g(stock_solution_id)
            if mass > available + 1e-12:
                raise InsufficientAvailableStockError(available, mass)
            event = await self.repository.add(
                LabInventoryReservationEvent(
                    reservation_id=str(uuid4()),
                    sequence=1,
                    parent_event_id=None,
                    build_plan_version_id=plan.id,
                    build_plan_line_id=line.id,
                    stock_solution_id=stock_solution_id,
                    state="RESERVED",
                    reserved_mass_g=mass,
                    idempotency_key=idempotency_key,
                    command_sha256=command_sha256,
                    actor=actor,
                    rationale=rationale,
                )
            )
            physical_balance = await self.repository.stock_balance_g(
                stock_solution_id
            )
            await self._append_inventory_movement(
                stock=stock,
                movement_type="RESERVATION",
                raw_quantity=mass,
                balance_before=physical_balance,
                balance_after=physical_balance,
                actor=actor,
                transaction_id=event.reservation_id,
                idempotency_key=f"movement:reservation:{event.id}",
                reason="inventory_reservation",
                mass_delta_g=0.0,
                build_plan_line_id=line.id,
                reservation_event_id=event.id,
            )
            active_line_ids = (
                await self.repository.active_reserved_build_line_ids(plan.id)
            )
            plan_lines = await self.repository.build_plan_lines(plan.id)
            if active_line_ids == {plan_line.id for plan_line in plan_lines}:
                command = await self._build_plan_command_from_version(
                    plan,
                    rationale="All executable lines have active reservations.",
                )
                await self._write_build_plan_version(
                    plan_id=plan.plan_id,
                    version_number=plan.version_number + 1,
                    parent=plan,
                    status="RESERVED",
                    author=plan.author,
                    reviewer=plan.reviewer,
                    reviewed_at=plan.reviewed_at,
                    command=command,
                )
            return event

    async def transition_reservation(
        self,
        reservation_id: str,
        next_state: str,
        *,
        idempotency_key: str,
        actor: str,
        rationale: str,
    ) -> LabInventoryReservationEvent:
        reservation_id = _text(reservation_id, "reservation_id")
        next_state = _text(next_state, "next_state")
        idempotency_key = _text(idempotency_key, "idempotency_key")
        actor = _text(actor, "actor")
        rationale = _text(rationale, "rationale")
        command_payload = {
            "schema": "a2-reservation-command-v1",
            "operation": "TRANSITION",
            "reservation_id": reservation_id,
            "next_state": next_state,
            "idempotency_key": idempotency_key,
            "actor": actor,
            "rationale": rationale,
        }
        command_sha256 = stable_json_hash(command_payload)
        async with self._transaction():
            replay = (
                await self.repository.reservation_event_for_idempotency(
                    idempotency_key
                )
            )
            if replay is not None:
                if replay.command_sha256 == command_sha256:
                    return replay
                raise PlanningConflictError(
                    "RESERVATION_IDEMPOTENCY_CONFLICT",
                    "Reservation idempotency key was reused for a different command.",
                )
            current = await self.repository.latest_reservation_event(
                reservation_id
            )
            if current is None:
                raise PlanningConflictError(
                    "RESERVATION_NOT_FOUND",
                    f"Reservation not found: {reservation_id}.",
                )
            if next_state not in RESERVATION_TRANSITIONS.get(
                current.state,
                set(),
            ):
                raise PlanningConflictError(
                    "INVALID_RESERVATION_TRANSITION",
                    f"Reservation cannot transition from {current.state} "
                    f"to {next_state}.",
                )
            event = await self.repository.add(
                LabInventoryReservationEvent(
                    reservation_id=current.reservation_id,
                    sequence=current.sequence + 1,
                    parent_event_id=current.id,
                    build_plan_version_id=current.build_plan_version_id,
                    build_plan_line_id=current.build_plan_line_id,
                    stock_solution_id=current.stock_solution_id,
                    state=next_state,
                    reserved_mass_g=current.reserved_mass_g,
                    idempotency_key=idempotency_key,
                    command_sha256=command_sha256,
                    actor=actor,
                    rationale=rationale,
                )
            )
            if next_state in {"RELEASED", "CANCELLED"}:
                stock = await self.repository.get_stock(
                    current.stock_solution_id
                )
                if stock is None:
                    raise PlanningConflictError(
                        "STOCK_SOLUTION_NOT_FOUND",
                        "Reservation stock solution no longer exists.",
                    )
                physical_balance = await self.repository.stock_balance_g(
                    stock.id
                )
                await self._append_inventory_movement(
                    stock=stock,
                    movement_type="RESERVATION_RELEASE",
                    raw_quantity=current.reserved_mass_g,
                    balance_before=physical_balance,
                    balance_after=physical_balance,
                    actor=actor,
                    transaction_id=event.reservation_id,
                    idempotency_key=(
                        f"movement:reservation-release:{event.id}"
                    ),
                    reason="inventory_reservation_release",
                    mass_delta_g=0.0,
                    build_plan_line_id=current.build_plan_line_id,
                    reservation_event_id=event.id,
                )
            return event


__all__ = [
    "BUILD_PLAN_TRANSITIONS",
    "BuildPlanInput",
    "BuildPlanLineInput",
    "InsufficientAvailableStockError",
    "InventoryMappingInput",
    "LabPlanningServiceMixin",
    "PlanningConflictError",
    "PlanningDomainError",
    "RESERVATION_TRANSITIONS",
    "TargetHypothesisInput",
    "TargetLineInput",
]
