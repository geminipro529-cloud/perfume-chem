"""Transactional application service for immutable laboratory history."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from math import isfinite
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lab import (
    LabApplication,
    LabBatch,
    LabBottle,
    LabBottleEvent,
    LabBottleEventEffect,
    LabExperiment,
    LabFormula,
    LabFormulaComponent,
    LabFormulaVersion,
    LabInventoryMovement,
    LabMaterial,
    LabMaterialAlias,
    LabObservation,
    LabOutcome,
    LabPairwiseComparison,
    LabPrediction,
    LabSample,
    LabStockSolution,
)
from app.repositories.lab import BottleLedgerState, LabRepository
from app.services.commercial_references import LabCommercialReferenceServiceMixin
from app.services.engine_jobs import LabEngineJobServiceMixin
from app.services.external_validation import LabExternalValidationServiceMixin
from app.services.instrumental_observations import (
    LabInstrumentalObservationServiceMixin,
)
from app.services.lab_analytical import LabAnalyticalAuthorityServiceMixin
from app.services.lab_backfill import LabBackfillServiceMixin
from app.services.lab_claims import LabClaimAuthorityServiceMixin
from app.services.lab_execution import LabExecutionServiceMixin
from app.services.lab_external_studies import LabExternalStudyServiceMixin
from app.services.lab_planning import LabPlanningServiceMixin
from app.services.lab_properties import LabPropertyServiceMixin
from app.services.lab_regulatory import LabRegulatoryAuthorityServiceMixin
from app.services.lab_rules import LabRuleServiceMixin
from app.services.lab_science import LabScienceServiceMixin
from app.services.lab_sources import LabSourceServiceMixin
from app.services.lab_thresholds import LabThresholdServiceMixin
from app.services.physical_lineage import LabPhysicalLineageServiceMixin
from app.services.stock_lineage import (
    StockLineageError,
    validate_formula_version_physical_lineage,
)

_EXACT_DECIMAL_TEXT_MAX_LENGTH = 128


def _canonical_decimal_text(value: Decimal) -> str:
    if value == 0:
        return "0"
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def _exact_decimal(value: object, field_name: str) -> tuple[Decimal, str]:
    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as error:
        raise ValueError(f"{field_name} must be a finite decimal quantity") from error
    if not decimal_value.is_finite():
        raise ValueError(f"{field_name} must be a finite decimal quantity")
    text_value = _canonical_decimal_text(decimal_value)
    if len(text_value) > _EXACT_DECIMAL_TEXT_MAX_LENGTH:
        raise ValueError(
            f"{field_name} exceeds the exact-decimal persistence limit"
        )
    try:
        projection = float(decimal_value)
    except (OverflowError, ValueError) as error:
        raise ValueError(f"{field_name} cannot be projected to legacy float") from error
    if not isfinite(projection):
        raise ValueError(f"{field_name} cannot be projected to legacy float")
    return decimal_value, text_value


def _submitted_decimal_text(value: object, field_name: str) -> str:
    """Return the caller's finite decimal spelling for immutable receipts."""

    text_value = str(value).strip()
    if not text_value or len(text_value) > _EXACT_DECIMAL_TEXT_MAX_LENGTH:
        raise ValueError(f"{field_name} exceeds the exact-decimal persistence limit")
    _exact_decimal(value, field_name)
    return text_value


def _semantic_sha256(payload: object) -> str:
    return sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()


def _require_sha256(value: str, field_name: str) -> str:
    normalized = value.strip().casefold()
    if len(normalized) != 64 or any(
        character not in "0123456789abcdef" for character in normalized
    ):
        raise ValueError(f"{field_name} must be a 64-character hexadecimal digest")
    return normalized


@dataclass(frozen=True, slots=True)
class FormulaComponentInput:
    """One explicitly based stock dose in an immutable formula version."""

    stock_solution_id: str
    requested_mass_g: Decimal
    requested_volume_ul: float | None = None
    role: str | None = None
    unit: str = "g"

    def __post_init__(self) -> None:
        stock_solution_id = self.stock_solution_id.strip()
        mass, _mass_text = _exact_decimal(
            self.requested_mass_g,
            "requested_mass_g",
        )
        volume = (
            float(self.requested_volume_ul)
            if self.requested_volume_ul is not None
            else None
        )
        role = self.role.strip() if self.role else None
        if not stock_solution_id:
            raise ValueError("stock_solution_id must not be empty")
        if mass <= 0:
            raise ValueError("requested_mass_g must be finite and greater than zero")
        if volume is not None and (not isfinite(volume) or volume <= 0):
            raise ValueError("requested_volume_ul must be finite and greater than zero")
        if self.unit != "g":
            raise ValueError("formula component unit must be g")
        object.__setattr__(self, "stock_solution_id", stock_solution_id)
        object.__setattr__(self, "requested_mass_g", mass)
        object.__setattr__(self, "requested_volume_ul", volume)
        object.__setattr__(self, "role", role)


class LabTransactionError(ValueError):
    """Base error for rejected laboratory commands."""


class StaleBottleStreamError(LabTransactionError):
    """Raised when a command was prepared from an older bottle state."""


class InsufficientStockError(LabTransactionError):
    """Raised when a stock movement would make inventory negative."""


class InsufficientBottleMassError(LabTransactionError):
    """Raised when a transfer exceeds reconstructed source mass."""


class IdempotencyConflictError(LabTransactionError):
    """Raised when a command identifier is reused for a different request."""


class AlreadyCompensatedError(LabTransactionError):
    """Raised when immutable history already contains a correction."""


class ConcurrentWriteError(LabTransactionError):
    """Raised when a write loses a database-level optimistic race."""


_LAB_WRITE_LOCK = asyncio.Lock()


class LabService(
    LabCommercialReferenceServiceMixin,
    LabEngineJobServiceMixin,
    LabInstrumentalObservationServiceMixin,
    LabExternalValidationServiceMixin,
    LabPhysicalLineageServiceMixin,
    LabExecutionServiceMixin,
    LabExternalStudyServiceMixin,
    LabBackfillServiceMixin,
    LabRuleServiceMixin,
    LabThresholdServiceMixin,
    LabPropertyServiceMixin,
    LabRegulatoryAuthorityServiceMixin,
    LabSourceServiceMixin,
    LabAnalyticalAuthorityServiceMixin,
    LabClaimAuthorityServiceMixin,
    LabScienceServiceMixin,
    LabPlanningServiceMixin,
):
    """Own transactions while delegating persistence to ``LabRepository``."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = LabRepository(session)

    @asynccontextmanager
    async def _transaction(self):
        """Join caller transactions; otherwise own one serialized write unit."""

        await _LAB_WRITE_LOCK.acquire()
        owns_transaction = not self.session.in_transaction()
        try:
            if owns_transaction:
                bind = self.session.get_bind()
                if bind.dialect.name == "sqlite":
                    await self.session.execute(text("BEGIN IMMEDIATE"))
                else:
                    await self.session.begin()
            try:
                yield
            except BaseException:
                if owns_transaction:
                    await self.session.rollback()
                raise
            else:
                if owns_transaction:
                    await self.session.commit()
        finally:
            _LAB_WRITE_LOCK.release()

    async def create_material(self, canonical_name: str) -> LabMaterial:
        name = canonical_name.strip()
        if not name:
            raise ValueError("canonical_name must not be empty")
        async with self._transaction():
            return await self.repository.add(LabMaterial(canonical_name=name))

    async def create_material_alias(
        self,
        material_id: str,
        alias: str,
    ) -> LabMaterialAlias:
        alias_text = alias.strip()
        if not alias_text:
            raise ValueError("alias must not be empty")
        async with self._transaction():
            if await self.repository.get_material(material_id) is None:
                raise KeyError(f"Unknown material: {material_id}")
            return await self.repository.add(
                LabMaterialAlias(
                    material_id=material_id,
                    alias=alias_text,
                    normalized_alias=alias_text.lower(),
                )
            )

    async def create_stock_solution(
        self,
        *,
        material_id: str,
        active_fraction: Decimal | int | float | str,
        fraction_basis: str,
        initial_mass_g: float,
        density_g_ml: float | None = None,
        supplier: str | None = None,
        lot_number: str | None = None,
        solvent_name: str | None = None,
    ) -> LabStockSolution:
        active_fraction_decimal, active_fraction_text = _exact_decimal(
            active_fraction,
            "active_fraction",
        )
        if not Decimal("0") < active_fraction_decimal <= Decimal("1"):
            raise ValueError("active_fraction must be greater than zero and at most one")
        if fraction_basis not in {"mass_fraction", "volume_fraction", "amount_fraction"}:
            raise ValueError("fraction_basis must be explicit")
        if initial_mass_g < 0:
            raise ValueError("initial_mass_g must be nonnegative")
        if density_g_ml is not None and density_g_ml <= 0:
            raise ValueError("density_g_ml must be greater than zero")
        async with self._transaction():
            if await self.repository.get_material(material_id) is None:
                raise KeyError(f"Unknown material: {material_id}")
            return await self.repository.add(
                LabStockSolution(
                    material_id=material_id,
                    active_fraction=float(active_fraction_decimal),
                    active_fraction_decimal_text=active_fraction_text,
                    fraction_basis=fraction_basis,
                    initial_mass_g=initial_mass_g,
                    remaining_mass_g=initial_mass_g,
                    density_g_ml=density_g_ml,
                    supplier=supplier,
                    lot_number=lot_number,
                    solvent_name=solvent_name,
                )
            )

    async def create_formula(self, name: str) -> LabFormula:
        name = name.strip()
        if not name:
            raise ValueError("formula name must not be empty")
        async with self._transaction():
            return await self.repository.add(LabFormula(name=name))

    async def add_formula_version(
        self,
        formula_id: str,
        *,
        brief: dict,
        constraints: dict,
        concentration_fraction: float | None = None,
        concentration_basis: str | None = None,
        source: dict | None = None,
        components: Sequence[FormulaComponentInput] = (),
    ) -> LabFormulaVersion:
        component_rows = tuple(components)
        stock_ids = [component.stock_solution_id for component in component_rows]
        if len(stock_ids) != len(set(stock_ids)):
            raise ValueError("formula components must not repeat a stock solution")
        async with self._transaction():
            if await self.repository.get_formula(formula_id) is None:
                raise KeyError(f"Unknown formula: {formula_id}")
            for component in component_rows:
                if await self.repository.get_stock(component.stock_solution_id) is None:
                    raise KeyError(
                        f"Unknown stock solution: {component.stock_solution_id}"
                    )
            version = LabFormulaVersion(
                formula_id=formula_id,
                version_number=await self.repository.next_formula_version(formula_id),
                brief_json=dict(brief),
                constraints_json=dict(constraints),
                concentration_fraction=concentration_fraction,
                concentration_basis=concentration_basis,
                source_json=dict(source or {}),
            )
            await self.repository.add(version)
            for position, component in enumerate(component_rows, start=1):
                await self.repository.add(
                    LabFormulaComponent(
                        formula_version_id=version.id,
                        stock_solution_id=component.stock_solution_id,
                        position=position,
                        requested_mass_g=float(component.requested_mass_g),
                        requested_mass_g_decimal_text=_canonical_decimal_text(
                            component.requested_mass_g
                        ),
                        requested_volume_ul=component.requested_volume_ul,
                        role=component.role,
                        unit=component.unit,
                    )
                )
            return version

    async def update_formula_version(self, _version_id: str, **_changes) -> None:
        raise ValueError("formula versions are immutable; create a new version")

    async def create_bottle(
        self,
        label: str,
        *,
        initial_mass_g: float = 0.0,
    ) -> LabBottle:
        if initial_mass_g < 0:
            raise ValueError("initial_mass_g must be nonnegative")
        async with self._transaction():
            bottle = await self.repository.add(LabBottle(label=label.strip()))
            event = await self.repository.add(
                LabBottleEvent(
                    bottle_id=bottle.id,
                    stream_sequence=1,
                    expected_sequence=0,
                    command_id=f"create-{bottle.id}",
                    transaction_id=str(uuid4()),
                    event_type="create",
                    payload_json={"initial_mass_g": initial_mass_g},
                )
            )
            if initial_mass_g:
                await self.repository.add(
                    LabBottleEventEffect(
                        event_id=event.id,
                        bottle_id=bottle.id,
                        mass_delta_g=initial_mass_g,
                    )
                )
            return bottle

    async def add_stock_to_bottle(
        self,
        *,
        bottle_id: str,
        stock_solution_id: str,
        mass_g: Decimal | int | float | str,
        expected_sequence: int,
        command_id: str,
        measured_volume_ul: Decimal | int | float | str | None = None,
        standard_uncertainty: Decimal | int | float | str | None = None,
        volume_standard_uncertainty_ul: Decimal | int | float | str | None = None,
        volume_measurement_method: str | None = None,
        volume_device_id: str | None = None,
        volume_device_calibration_sha256: str | None = None,
        volume_reference_temperature_c: Decimal | int | float | str | None = None,
        volume_reference_conditions: dict | None = None,
        actor: str = "system",
        goal_analysis_sha256: str | None = None,
        hypothesis_id: str | None = None,
        hypothesis_variant: str | None = None,
    ) -> LabBottleEvent:
        async with self._transaction():
            return await self._add_stock_to_bottle_in_transaction(
                bottle_id=bottle_id,
                stock_solution_id=stock_solution_id,
                mass_g=mass_g,
                expected_sequence=expected_sequence,
                command_id=command_id,
                measured_volume_ul=measured_volume_ul,
                standard_uncertainty=standard_uncertainty,
                volume_standard_uncertainty_ul=volume_standard_uncertainty_ul,
                volume_measurement_method=volume_measurement_method,
                volume_device_id=volume_device_id,
                volume_device_calibration_sha256=volume_device_calibration_sha256,
                volume_reference_temperature_c=volume_reference_temperature_c,
                volume_reference_conditions=volume_reference_conditions,
                actor=actor,
                goal_analysis_sha256=goal_analysis_sha256,
                hypothesis_id=hypothesis_id,
                hypothesis_variant=hypothesis_variant,
            )

    async def _add_stock_to_bottle_in_transaction(
        self,
        *,
        bottle_id: str,
        stock_solution_id: str,
        mass_g: Decimal | int | float | str,
        expected_sequence: int,
        command_id: str,
        measured_volume_ul: Decimal | int | float | str | None = None,
        standard_uncertainty: Decimal | int | float | str | None = None,
        volume_standard_uncertainty_ul: Decimal | int | float | str | None = None,
        volume_measurement_method: str | None = None,
        volume_device_id: str | None = None,
        volume_device_calibration_sha256: str | None = None,
        volume_reference_temperature_c: Decimal | int | float | str | None = None,
        volume_reference_conditions: dict | None = None,
        actor: str = "system",
        build_plan_line_id: str | None = None,
        reservation_event_id: str | None = None,
        event_type: str = "ADD_MATERIAL",
        goal_analysis_sha256: str | None = None,
        hypothesis_id: str | None = None,
        hypothesis_variant: str | None = None,
    ) -> LabBottleEvent:
        """Apply one stock addition inside the caller's canonical transaction."""

        mass_decimal, mass_canonical = _exact_decimal(mass_g, "mass_g")
        mass_submitted = _submitted_decimal_text(mass_g, "mass_g")
        mass_projection = float(mass_decimal)
        if mass_decimal <= 0:
            raise ValueError("mass_g must be greater than zero")

        measured_volume_projection: float | None = None
        measured_volume_submitted: str | None = None
        measured_volume_canonical: str | None = None
        if measured_volume_ul is not None:
            measured_volume_decimal, measured_volume_canonical = _exact_decimal(
                measured_volume_ul,
                "measured_volume_ul",
            )
            measured_volume_submitted = _submitted_decimal_text(
                measured_volume_ul,
                "measured_volume_ul",
            )
            if measured_volume_decimal <= 0:
                raise ValueError("measured_volume_ul must be greater than zero")
            measured_volume_projection = float(measured_volume_decimal)

        uncertainty_projection: float | None = None
        uncertainty_submitted: str | None = None
        uncertainty_canonical: str | None = None
        if standard_uncertainty is not None:
            uncertainty_decimal, uncertainty_canonical = _exact_decimal(
                standard_uncertainty,
                "standard_uncertainty",
            )
            uncertainty_submitted = _submitted_decimal_text(
                standard_uncertainty,
                "standard_uncertainty",
            )
            if uncertainty_decimal < 0:
                raise ValueError("standard_uncertainty must be nonnegative")
            uncertainty_projection = float(uncertainty_decimal)

        volume_uncertainty_projection: float | None = None
        volume_uncertainty_submitted: str | None = None
        volume_uncertainty_canonical: str | None = None
        if volume_standard_uncertainty_ul is not None:
            volume_uncertainty_decimal, volume_uncertainty_canonical = _exact_decimal(
                volume_standard_uncertainty_ul,
                "volume_standard_uncertainty_ul",
            )
            volume_uncertainty_submitted = _submitted_decimal_text(
                volume_standard_uncertainty_ul,
                "volume_standard_uncertainty_ul",
            )
            if volume_uncertainty_decimal < 0:
                raise ValueError("volume_standard_uncertainty_ul must be nonnegative")
            volume_uncertainty_projection = float(volume_uncertainty_decimal)

        temperature_projection: float | None = None
        temperature_submitted: str | None = None
        temperature_canonical: str | None = None
        if volume_reference_temperature_c is not None:
            temperature_decimal, temperature_canonical = _exact_decimal(
                volume_reference_temperature_c,
                "volume_reference_temperature_c",
            )
            temperature_submitted = _submitted_decimal_text(
                volume_reference_temperature_c,
                "volume_reference_temperature_c",
            )
            temperature_projection = float(temperature_decimal)

        calibration_hash = (
            _require_sha256(
                volume_device_calibration_sha256,
                "volume_device_calibration_sha256",
            )
            if volume_device_calibration_sha256 is not None
            else None
        )
        actor = actor.strip()
        if not actor:
            raise ValueError("actor must not be empty")
        if event_type not in {"ADD_MATERIAL", "ADD_SOLVENT"}:
            raise ValueError(f"unsupported addition event_type: {event_type}")
        if (build_plan_line_id is None) != (reservation_event_id is None):
            raise LabTransactionError(
                "planned execution requires both build-plan line and reservation lineage"
            )
        planned_lifecycle = (
            build_plan_line_id is not None and reservation_event_id is not None
        )
        personal_context_values = (
            goal_analysis_sha256,
            hypothesis_id,
            hypothesis_variant,
        )
        if any(value is not None for value in personal_context_values) and not all(
            value is not None for value in personal_context_values
        ):
            raise ValueError(
                "goal analysis hash, hypothesis ID, and hypothesis variant must be supplied together"
            )
        personal_research_context: dict[str, str] | None = None
        if goal_analysis_sha256 is not None:
            variant = str(hypothesis_variant).strip()
            if variant not in {"low_variant", "high_variant"}:
                raise ValueError(f"unsupported hypothesis variant: {variant}")
            personal_research_context = {
                "goal_analysis_sha256": _require_sha256(
                    goal_analysis_sha256,
                    "goal_analysis_sha256",
                ),
                "hypothesis_id": str(hypothesis_id).strip(),
                "hypothesis_variant": variant,
            }
            if not personal_research_context["hypothesis_id"]:
                raise ValueError("hypothesis_id must not be empty")
        token = _command_token("add-stock", command_id)
        legacy_request_payload = {
            "stock_solution_id": stock_solution_id,
            "mass_g": mass_projection,
            "measured_volume_ul": measured_volume_projection,
            "standard_uncertainty": uncertainty_projection,
            "expected_sequence": expected_sequence,
            "event_type": event_type,
        }
        request_payload = {
            **legacy_request_payload,
            "mass_g_decimal_text": mass_canonical,
            "mass_g_submitted_decimal_text": mass_submitted,
            "measured_volume_ul_decimal_text": measured_volume_submitted,
            "measured_volume_ul_submitted_decimal_text": measured_volume_submitted,
            "measured_volume_ul_canonical_decimal_text": measured_volume_canonical,
            "standard_uncertainty_decimal_text": uncertainty_canonical,
            "standard_uncertainty_submitted_decimal_text": uncertainty_submitted,
            "volume_standard_uncertainty_ul": volume_uncertainty_projection,
            "volume_standard_uncertainty_ul_decimal_text": volume_uncertainty_submitted,
            "volume_standard_uncertainty_ul_submitted_decimal_text": (
                volume_uncertainty_submitted
            ),
            "volume_standard_uncertainty_ul_canonical_decimal_text": (
                volume_uncertainty_canonical
            ),
            "volume_measurement_method": (
                volume_measurement_method.strip()
                if volume_measurement_method is not None
                else None
            ),
            "volume_device_id": (
                volume_device_id.strip() if volume_device_id is not None else None
            ),
            "volume_device_calibration_sha256": calibration_hash,
            "volume_reference_temperature_c": temperature_projection,
            "volume_reference_temperature_c_decimal_text": temperature_submitted,
            "volume_reference_temperature_c_submitted_decimal_text": (
                temperature_submitted
            ),
            "volume_reference_temperature_c_canonical_decimal_text": (
                temperature_canonical
            ),
            "volume_reference_conditions": (
                dict(volume_reference_conditions)
                if volume_reference_conditions is not None
                else None
            ),
            "execution_scope": (
                "PLANNED_PROPOSAL_CONFIRM_MEASURE_COMMIT"
                if planned_lifecycle
                else "FREEFORM_UNBOUND_QUARANTINE"
            ),
            "formula_execution_authority": False,
            "build_plan_fulfillment_authority": planned_lifecycle,
            **(
                {"personal_research_context": personal_research_context}
                if personal_research_context is not None
                else {}
            ),
        }
        existing = await self.repository.event_for_command(bottle_id, token)
        if existing is not None:
            if existing.payload_json not in (
                request_payload,
                legacy_request_payload,
            ):
                raise IdempotencyConflictError(
                    "command identifier was already used for a different request"
                )
            return existing
        bottle = await self.repository.get_bottle(bottle_id)
        stock = await self.repository.get_stock(stock_solution_id)
        if bottle is None:
            raise KeyError(f"Unknown bottle: {bottle_id}")
        if stock is None:
            raise KeyError(f"Unknown stock solution: {stock_solution_id}")
        if bottle.batch_id is not None and (
            build_plan_line_id is None or reservation_event_id is None
        ):
            raise LabTransactionError(
                "formula/batch-bound bottles require proposal-confirm-measure-commit execution"
            )
        if bottle.batch_id is not None:
            batch = await self.session.get(LabBatch, bottle.batch_id)
            if batch is None:
                raise LabTransactionError("batch-bound bottle references a missing batch")
            try:
                await validate_formula_version_physical_lineage(
                    self.session,
                    batch.formula_version_id,
                )
            except StockLineageError as error:
                raise LabTransactionError(
                    f"{error.code}: {error}"
                ) from error
        if await self.repository.bottle_is_closed(bottle_id):
            raise LabTransactionError("bottle is closed")
        current_sequence = await self.repository.latest_sequence(bottle_id)
        if current_sequence != expected_sequence:
            raise StaleBottleStreamError(
                f"expected sequence {expected_sequence}, current sequence is {current_sequence}"
            )
        physical_balance_g = await self.repository.stock_balance_g(
            stock_solution_id
        )
        available_g = physical_balance_g
        if not planned_lifecycle:
            available_g -= await self.repository.active_reserved_mass_g(
                stock_solution_id
            )
        if mass_projection > available_g + 1e-12:
            raise InsufficientStockError(
                f"requested {mass_projection:g} g but only {available_g:g} g is available"
            )

        event = await self.repository.add(
            LabBottleEvent(
                bottle_id=bottle_id,
                stream_sequence=current_sequence + 1,
                expected_sequence=expected_sequence,
                command_id=token,
                transaction_id=str(uuid4()),
                event_type=event_type,
                payload_json=request_payload,
            )
        )
        effect = await self.repository.add(
            LabBottleEventEffect(
                event_id=event.id,
                bottle_id=bottle_id,
                stock_solution_id=stock_solution_id,
                material_id=stock.material_id,
                mass_delta_g=mass_projection,
                measured_volume_ul=measured_volume_projection,
                density_g_ml=stock.density_g_ml,
            )
        )
        await self._append_inventory_movement(
            stock=stock,
            movement_type="CONSUMPTION",
            raw_quantity=mass_projection,
            balance_before=physical_balance_g,
            balance_after=physical_balance_g - mass_projection,
            actor=actor,
            transaction_id=event.transaction_id,
            idempotency_key=f"movement:{event.id}",
            reason="bottle_addition",
            mass_delta_g=-mass_projection,
            event_effect_id=effect.id,
            bottle_event_id=event.id,
            build_plan_line_id=build_plan_line_id,
            reservation_event_id=reservation_event_id,
            measured_volume_ul=measured_volume_projection,
            standard_uncertainty=uncertainty_projection,
        )
        stock.remaining_mass_g = physical_balance_g - mass_projection
        return event

    async def add_solvent_to_bottle(
        self,
        *,
        bottle_id: str,
        stock_solution_id: str,
        mass_g: Decimal | int | float | str,
        expected_sequence: int,
        command_id: str,
        measured_volume_ul: Decimal | int | float | str | None = None,
        standard_uncertainty: Decimal | int | float | str | None = None,
        volume_standard_uncertainty_ul: Decimal | int | float | str | None = None,
        volume_measurement_method: str | None = None,
        volume_device_id: str | None = None,
        volume_device_calibration_sha256: str | None = None,
        volume_reference_temperature_c: Decimal | int | float | str | None = None,
        volume_reference_conditions: dict | None = None,
        actor: str = "system",
        goal_analysis_sha256: str | None = None,
        hypothesis_id: str | None = None,
        hypothesis_variant: str | None = None,
    ) -> LabBottleEvent:
        """Append a solvent addition without classifying it as odorant mass."""

        async with self._transaction():
            return await self._add_stock_to_bottle_in_transaction(
                bottle_id=bottle_id,
                stock_solution_id=stock_solution_id,
                mass_g=mass_g,
                expected_sequence=expected_sequence,
                command_id=command_id,
                measured_volume_ul=measured_volume_ul,
                standard_uncertainty=standard_uncertainty,
                volume_standard_uncertainty_ul=volume_standard_uncertainty_ul,
                volume_measurement_method=volume_measurement_method,
                volume_device_id=volume_device_id,
                volume_device_calibration_sha256=volume_device_calibration_sha256,
                volume_reference_temperature_c=volume_reference_temperature_c,
                volume_reference_conditions=volume_reference_conditions,
                actor=actor,
                event_type="ADD_SOLVENT",
                goal_analysis_sha256=goal_analysis_sha256,
                hypothesis_id=hypothesis_id,
                hypothesis_variant=hypothesis_variant,
            )

    async def finalize_stock_preparation(
        self,
        *,
        bottle_id: str,
        material_id: str,
        parent_event_id: str,
        carrier_event_id: str,
        parent_identity_evidence_id: str,
        carrier_identity_evidence_id: str,
        child_label: str,
        child_lot_number: str,
        preparation_sop_sha256: str,
        balance_calibration_sha256: str,
        command_id: str,
        actor: str,
        source_design_sha256: str | None = None,
        source_target_volume_fraction: Decimal | int | float | str | None = None,
    ) -> LabStockSolution:
        """Create one mass-authoritative child stock from a closed bottle.

        Component delivery volumes are retained only as source-intent metadata.
        They never change committed mass, inventory balances, the canonical
        mass-fraction basis, or any action authority.
        """

        label = child_label.strip()
        lot = child_lot_number.strip()
        operator = actor.strip()
        if not label or not lot or not operator:
            raise ValueError("child_label, child_lot_number, and actor must not be empty")
        sop_hash = _require_sha256(preparation_sop_sha256, "preparation_sop_sha256")
        balance_hash = _require_sha256(
            balance_calibration_sha256,
            "balance_calibration_sha256",
        )
        design_hash = (
            _require_sha256(source_design_sha256, "source_design_sha256")
            if source_design_sha256 is not None
            else None
        )
        if (design_hash is None) != (source_target_volume_fraction is None):
            raise ValueError(
                "source_design_sha256 and source_target_volume_fraction must be supplied together"
            )

        target_volume_fraction: Decimal | None = None
        target_volume_fraction_submitted: str | None = None
        target_volume_fraction_canonical: str | None = None
        if source_target_volume_fraction is not None:
            (
                target_volume_fraction,
                target_volume_fraction_canonical,
            ) = _exact_decimal(
                source_target_volume_fraction,
                "source_target_volume_fraction",
            )
            target_volume_fraction_submitted = _submitted_decimal_text(
                source_target_volume_fraction,
                "source_target_volume_fraction",
            )
            if not Decimal("0") < target_volume_fraction < Decimal("1"):
                raise ValueError(
                    "source_target_volume_fraction must be greater than zero and less than one"
                )

        command_token = _command_token("finalize-stock-preparation", command_id)
        command_payload = {
            "bottle_id": bottle_id,
            "material_id": material_id,
            "parent_event_id": parent_event_id,
            "carrier_event_id": carrier_event_id,
            "parent_identity_evidence_id": parent_identity_evidence_id,
            "carrier_identity_evidence_id": carrier_identity_evidence_id,
            "child_label": label,
            "child_lot_number": lot,
            "preparation_sop_sha256": sop_hash,
            "balance_calibration_sha256": balance_hash,
            "source_design_sha256": design_hash,
            "source_target_volume_fraction": target_volume_fraction_submitted,
            "canonical_source_target_volume_fraction": (
                target_volume_fraction_canonical
            ),
            "actor": operator,
        }
        command_sha256 = _semantic_sha256(command_payload)

        async with self._transaction():
            replay = await self.repository.stock_preparation_for_command(command_token)
            if replay is not None:
                receipt = dict(replay.source_json or {}).get(
                    "stock_preparation_receipt",
                    {},
                )
                if receipt.get("command_sha256") != command_sha256:
                    raise IdempotencyConflictError(
                        "command identifier was already used for a different request"
                    )
                return replay
            prior_bottle_result = await self.repository.stock_preparation_for_bottle(
                bottle_id
            )
            if prior_bottle_result is not None:
                raise IdempotencyConflictError(
                    "preparation bottle was already finalized under another command"
                )

            bottle = await self.repository.get_bottle(bottle_id)
            if bottle is None:
                raise KeyError(f"Unknown bottle: {bottle_id}")
            material = await self.repository.get_material(material_id)
            if material is None:
                raise KeyError(f"Unknown material: {material_id}")
            events = await self.repository.events_for_bottle(bottle_id)
            if not events or events[-1].event_type != "CLOSE_BATCH":
                raise LabTransactionError(
                    "stock preparation requires a terminal close event"
                )
            close_event = events[-1]
            addition_events = [
                event
                for event in events
                if event.event_type in {"ADD_MATERIAL", "ADD_SOLVENT"}
            ]
            if len(addition_events) != 2 or {
                event.id for event in addition_events
            } != {parent_event_id, carrier_event_id}:
                raise LabTransactionError(
                    "stock preparation requires exactly one parent and one carrier addition"
                )

            parent_event = await self.repository.get_event(parent_event_id)
            carrier_event = await self.repository.get_event(carrier_event_id)
            if (
                parent_event is None
                or carrier_event is None
                or parent_event.bottle_id != bottle_id
                or carrier_event.bottle_id != bottle_id
                or parent_event.event_type != "ADD_MATERIAL"
                or carrier_event.event_type != "ADD_SOLVENT"
            ):
                raise LabTransactionError(
                    "stock preparation parent/carrier events do not match the closed bottle"
                )
            if (
                await self.repository.correction_for_event(parent_event_id) is not None
                or await self.repository.correction_for_event(carrier_event_id) is not None
            ):
                raise LabTransactionError(
                    "corrected or reversed preparation input history is not admissible"
                )

            parent_effects = await self.repository.effects_for_event(parent_event_id)
            carrier_effects = await self.repository.effects_for_event(carrier_event_id)
            if len(parent_effects) != 1 or len(carrier_effects) != 1:
                raise LabTransactionError(
                    "stock preparation inputs require exactly one committed effect each"
                )
            parent_effect = parent_effects[0]
            carrier_effect = carrier_effects[0]
            if (
                parent_effect.stock_solution_id is None
                or carrier_effect.stock_solution_id is None
            ):
                raise LabTransactionError(
                    "stock preparation input effects must bind exact stock solutions"
                )
            parent_stock = await self.repository.get_stock(parent_effect.stock_solution_id)
            carrier_stock = await self.repository.get_stock(carrier_effect.stock_solution_id)
            if parent_stock is None or carrier_stock is None:
                raise LabTransactionError(
                    "stock preparation input stock solution is unavailable"
                )
            if parent_stock.material_id != material_id:
                raise LabTransactionError(
                    "prepared-stock material must match the parent stock material"
                )
            if (
                parent_stock.fraction_basis != "mass_fraction"
                or carrier_stock.fraction_basis != "mass_fraction"
            ):
                raise LabTransactionError(
                    "executed stock preparation requires mass_fraction input authority"
                )

            parent_evidence = await self.repository.get_evidence_record(
                parent_identity_evidence_id
            )
            carrier_evidence = await self.repository.get_evidence_record(
                carrier_identity_evidence_id
            )
            if parent_evidence is None or carrier_evidence is None:
                raise LabTransactionError(
                    "stock preparation identity evidence record is unavailable"
                )
            if (
                parent_evidence.classification != "EXACT"
                or carrier_evidence.classification != "EXACT"
            ):
                raise LabTransactionError(
                    "stock preparation identity evidence must be classified EXACT"
                )

            def event_decimal(
                event: LabBottleEvent,
                field: str,
                *,
                required: bool = True,
            ) -> tuple[Decimal | None, str | None, str | None]:
                payload = event.payload_json
                submitted = payload.get(f"{field}_submitted_decimal_text")
                canonical = payload.get(f"{field}_decimal_text")
                if field == "measured_volume_ul":
                    canonical = payload.get(
                        "measured_volume_ul_canonical_decimal_text",
                        canonical,
                    )
                if field == "volume_standard_uncertainty_ul":
                    canonical = payload.get(
                        "volume_standard_uncertainty_ul_canonical_decimal_text",
                        canonical,
                    )
                if field == "volume_reference_temperature_c":
                    canonical = payload.get(
                        "volume_reference_temperature_c_canonical_decimal_text",
                        canonical,
                    )
                raw_value = payload.get(field)
                if canonical is None and raw_value is not None:
                    value, canonical = _exact_decimal(raw_value, field)
                    submitted = submitted or str(raw_value)
                    return value, submitted, canonical
                if canonical is None:
                    if required:
                        raise LabTransactionError(
                            f"stock preparation requires {field} authority"
                        )
                    return None, None, None
                value, normalized = _exact_decimal(canonical, field)
                return value, submitted or str(canonical), normalized

            parent_mass, _parent_mass_submitted, parent_mass_text = event_decimal(
                parent_event,
                "mass_g",
            )
            carrier_mass, _carrier_mass_submitted, carrier_mass_text = event_decimal(
                carrier_event,
                "mass_g",
            )
            parent_uncertainty, _unused, parent_uncertainty_text = event_decimal(
                parent_event,
                "standard_uncertainty",
                required=False,
            )
            carrier_uncertainty, _unused, carrier_uncertainty_text = event_decimal(
                carrier_event,
                "standard_uncertainty",
                required=False,
            )
            if parent_uncertainty is None or carrier_uncertainty is None:
                raise LabTransactionError(
                    "stock preparation requires standard uncertainty for both mass inputs"
                )
            assert parent_mass is not None and carrier_mass is not None
            total_mass = parent_mass + carrier_mass
            if total_mass <= 0:
                raise LabTransactionError(
                    "stock preparation child mass must be greater than zero"
                )
            parent_fraction, _fraction_text = _exact_decimal(
                parent_stock.active_fraction_decimal_text
                or parent_stock.active_fraction,
                "parent_active_fraction",
            )
            active_mass = parent_mass * parent_fraction
            child_fraction = active_mass / total_mass
            total_mass_text = _canonical_decimal_text(total_mass)
            active_mass_text = _canonical_decimal_text(active_mass)
            child_fraction_text = _canonical_decimal_text(child_fraction)

            carrier_material = await self.repository.get_material(
                carrier_stock.material_id
            )
            if carrier_material is None:
                raise LabTransactionError(
                    "stock preparation carrier material is unavailable"
                )

            def volume_delivery(event: LabBottleEvent) -> dict:
                volume, submitted_volume, canonical_volume = event_decimal(
                    event,
                    "measured_volume_ul",
                )
                uncertainty, submitted_uncertainty, canonical_uncertainty = event_decimal(
                    event,
                    "volume_standard_uncertainty_ul",
                    required=False,
                )
                if uncertainty is None:
                    raise LabTransactionError(
                        "source v/v intent requires volume_standard_uncertainty_ul authority"
                    )
                temperature, submitted_temperature, canonical_temperature = event_decimal(
                    event,
                    "volume_reference_temperature_c",
                    required=False,
                )
                payload = event.payload_json
                conditions = payload.get("volume_reference_conditions")
                if temperature is None or not isinstance(conditions, dict) or not conditions:
                    raise LabTransactionError(
                        "source v/v intent requires volume_reference_conditions authority"
                    )
                method = payload.get("volume_measurement_method")
                device_id = payload.get("volume_device_id")
                calibration = payload.get("volume_device_calibration_sha256")
                if not method or not device_id or not calibration:
                    raise LabTransactionError(
                        "source v/v intent requires complete volume measurement provenance"
                    )
                assert volume is not None
                return {
                    "measured_volume_ul": submitted_volume,
                    "canonical_measured_volume_ul": canonical_volume,
                    "standard_uncertainty_ul": submitted_uncertainty,
                    "canonical_standard_uncertainty_ul": canonical_uncertainty,
                    "unit": "uL",
                    "measurement_method": method,
                    "device_id": device_id,
                    "device_calibration_sha256": calibration,
                    "reference_temperature_c": submitted_temperature,
                    "canonical_reference_temperature_c": canonical_temperature,
                    "reference_conditions": dict(conditions),
                }

            parent_record: dict[str, object] = {
                "event_id": parent_event.id,
                "stock_solution_id": parent_stock.id,
                "material_id": parent_stock.material_id,
                "identity_evidence_id": parent_identity_evidence_id,
                "measured_mass_g": parent_mass_text,
                "standard_uncertainty_g": parent_uncertainty_text,
                "active_fraction": _canonical_decimal_text(parent_fraction),
                "fraction_basis": parent_stock.fraction_basis,
            }
            carrier_record: dict[str, object] = {
                "event_id": carrier_event.id,
                "stock_solution_id": carrier_stock.id,
                "material_id": carrier_stock.material_id,
                "identity_evidence_id": carrier_identity_evidence_id,
                "measured_mass_g": carrier_mass_text,
                "standard_uncertainty_g": carrier_uncertainty_text,
                "fraction_basis": carrier_stock.fraction_basis,
            }

            source_volume_intent: dict | None = None
            schema_version = "lab-stock-preparation-receipt-v1"
            if target_volume_fraction is not None:
                schema_version = "lab-stock-preparation-receipt-v2"
                parent_delivery = volume_delivery(parent_event)
                carrier_delivery = volume_delivery(carrier_event)
                parent_record["volume_delivery"] = parent_delivery
                carrier_record["volume_delivery"] = carrier_delivery
                parent_volume = Decimal(parent_delivery["canonical_measured_volume_ul"])
                carrier_volume = Decimal(carrier_delivery["canonical_measured_volume_ul"])
                total_volume = parent_volume + carrier_volume
                if total_volume <= 0:
                    raise LabTransactionError(
                        "source v/v intent requires positive component delivery volume"
                    )
                observed_fraction = parent_volume / total_volume
                conditions_compatible = (
                    parent_delivery["canonical_reference_temperature_c"]
                    == carrier_delivery["canonical_reference_temperature_c"]
                    and parent_delivery["reference_conditions"]
                    == carrier_delivery["reference_conditions"]
                )
                if not conditions_compatible:
                    alignment_state = "HOLD_INCOMPATIBLE_VOLUME_CONDITIONS"
                elif observed_fraction != target_volume_fraction:
                    alignment_state = "HOLD_VOLUME_RATIO_MISMATCH"
                else:
                    alignment_state = "NOMINAL_SOURCE_RATIO_MATCH_ONLY"
                source_volume_intent = {
                    "authority": (
                        "NONAUTHORITATIVE_PREPARATION_INTENT_AND_MEASUREMENT_METADATA"
                    ),
                    "source_target_grain": "PLANNED",
                    "observed_volume_grain": "MEASURED_COMPONENT_DELIVERIES",
                    "inventory_movement_grain": "COMMITTED_MASS_ONLY",
                    "correction_policy": (
                        "CORRECTED_OR_REVERSED_INPUT_HISTORY_REJECTED"
                    ),
                    "source_design_sha256": design_hash,
                    "definition": (
                        "IUPAC_VOLUME_FRACTION_COMPONENT_VOLUMES_BEFORE_MIXING"
                    ),
                    "denominator": (
                        "SUM_OF_SEPARATELY_MEASURED_COMPONENT_DELIVERY_VOLUMES_BEFORE_MIXING"
                    ),
                    "target_parent_input_volume_fraction": (
                        target_volume_fraction_submitted
                    ),
                    "canonical_target_parent_input_volume_fraction": (
                        target_volume_fraction_canonical
                    ),
                    "fraction_unit": "1",
                    "observed_parent_input_volume_fraction": (
                        _canonical_decimal_text(observed_fraction)
                    ),
                    "total_pre_mix_component_volume_ul": (
                        _canonical_decimal_text(total_volume)
                    ),
                    "alignment_state": alignment_state,
                    "conditions_compatible": conditions_compatible,
                    "final_mixed_solution_volume_used": False,
                    "canonical_stock_fraction_basis": "mass_fraction",
                    "inventory_authority": False,
                    "formula_dose_authority": False,
                    "mass_volume_conversion_authority": False,
                    "active_mass_or_dose_authority": False,
                    "volume_fraction_stock_created": False,
                    "exact_stock_ref_gate_satisfied": False,
                    "preparation_gate_satisfied": False,
                    "safety_authority": False,
                    "execution_authority": False,
                    "scientific_authority": False,
                    "release_authority": False,
                }

            unsigned_receipt = {
                "schema_version": schema_version,
                "state": "EXECUTED_PREPARATION_RECORDED",
                "command_token": command_token,
                "command_sha256": command_sha256,
                "command": command_payload,
                "preparation_bottle": {
                    "bottle_id": bottle_id,
                    "label": bottle.label,
                    "close_event_id": close_event.id,
                    "close_stream_sequence": close_event.stream_sequence,
                },
                "parent": parent_record,
                "carrier": carrier_record,
                "child": {
                    "material_id": material_id,
                    "label": label,
                    "lot_number": lot,
                    "initial_mass_g": total_mass_text,
                    "active_mass_g": active_mass_text,
                    "active_fraction": child_fraction_text,
                    "fraction_basis": "mass_fraction",
                    "carrier_material_id": carrier_material.id,
                    "carrier_name": carrier_material.canonical_name,
                },
                "inventory_conservation": {
                    "parent_consumed_mass_g": parent_mass_text,
                    "carrier_consumed_mass_g": carrier_mass_text,
                    "child_initial_mass_g": total_mass_text,
                    "mass_delta_g": "0",
                },
                "preparation_provenance": {
                    "preparation_sop_sha256": sop_hash,
                    "balance_calibration_sha256": balance_hash,
                    "operator": operator,
                },
                "authority": {
                    "formula_authority": False,
                    "safety_authority": False,
                    "scientific_authority": False,
                    "sensory_authority": False,
                    "release_authority": False,
                },
            }
            if source_volume_intent is not None:
                unsigned_receipt["source_volume_intent"] = source_volume_intent
            receipt = {
                **unsigned_receipt,
                "receipt_sha256": _semantic_sha256(unsigned_receipt),
            }
            return await self.repository.add(
                LabStockSolution(
                    material_id=material_id,
                    supplier="IN_HOUSE_PREPARATION",
                    lot_number=lot,
                    active_fraction=float(child_fraction),
                    active_fraction_decimal_text=child_fraction_text,
                    fraction_basis="mass_fraction",
                    solvent_name=carrier_material.canonical_name,
                    initial_mass_g=float(total_mass),
                    remaining_mass_g=float(total_mass),
                    source_json={"stock_preparation_receipt": receipt},
                )
            )

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
    ) -> LabInventoryMovement:
        if movement_type in {"CONSUMPTION", "RESERVATION"} and stock.fraction_basis != "mass_fraction":
            raise LabTransactionError(
                "mass-governed physical inventory movements require mass_fraction stock authority"
            )
        return await self.repository.add(
            LabInventoryMovement(
                stock_solution_id=stock.id,
                event_effect_id=event_effect_id,
                build_plan_line_id=build_plan_line_id,
                reservation_event_id=reservation_event_id,
                bottle_event_id=bottle_event_id,
                movement_type=movement_type,
                raw_quantity=raw_quantity,
                active_quantity=raw_quantity * stock.active_fraction,
                unit="g",
                basis="mass",
                balance_before=balance_before,
                balance_after=balance_after,
                standard_uncertainty=standard_uncertainty,
                actor=actor,
                transaction_id=transaction_id,
                idempotency_key=idempotency_key,
                admin_cause=admin_cause,
                correction_of_movement_id=correction_of_movement_id,
                reversal_of_movement_id=reversal_of_movement_id,
                mass_delta_g=mass_delta_g,
                measured_volume_ul=measured_volume_ul,
                reason=reason,
            )
        )

    async def _append_bottle_metadata_event(
        self,
        *,
        bottle_id: str,
        event_type: str,
        expected_sequence: int,
        command_id: str,
        actor: str,
        payload: dict,
    ) -> LabBottleEvent:
        actor = actor.strip()
        if not actor:
            raise ValueError("actor must not be empty")
        token = _command_token(event_type.lower(), command_id)
        request_payload = {
            **payload,
            "actor": actor,
            "expected_sequence": expected_sequence,
        }
        async with self._transaction():
            existing = await self.repository.event_for_command(
                bottle_id,
                token,
            )
            if existing is not None:
                if existing.payload_json != request_payload:
                    raise IdempotencyConflictError(
                        "command identifier was already used for a different request"
                    )
                return existing
            if await self.repository.get_bottle(bottle_id) is None:
                raise KeyError(f"Unknown bottle: {bottle_id}")
            current_sequence = await self.repository.latest_sequence(bottle_id)
            if current_sequence != expected_sequence:
                raise StaleBottleStreamError(
                    f"expected sequence {expected_sequence}, "
                    f"current sequence is {current_sequence}"
                )
            if (
                event_type == "CLOSE_BATCH"
                and await self.repository.bottle_is_closed(bottle_id)
            ):
                raise LabTransactionError("bottle is already closed")
            return await self.repository.add(
                LabBottleEvent(
                    bottle_id=bottle_id,
                    stream_sequence=current_sequence + 1,
                    expected_sequence=expected_sequence,
                    command_id=token,
                    transaction_id=str(uuid4()),
                    event_type=event_type,
                    payload_json=request_payload,
                )
            )

    async def tare_bottle(
        self,
        *,
        bottle_id: str,
        tare_mass_g: float,
        expected_sequence: int,
        command_id: str,
        actor: str,
    ) -> LabBottleEvent:
        if tare_mass_g < 0:
            raise ValueError("tare_mass_g must be nonnegative")
        return await self._append_bottle_metadata_event(
            bottle_id=bottle_id,
            event_type="TARE_CONTAINER",
            expected_sequence=expected_sequence,
            command_id=command_id,
            actor=actor,
            payload={"tare_mass_g": tare_mass_g},
        )

    async def close_bottle(
        self,
        *,
        bottle_id: str,
        expected_sequence: int,
        command_id: str,
        actor: str,
    ) -> LabBottleEvent:
        return await self._append_bottle_metadata_event(
            bottle_id=bottle_id,
            event_type="CLOSE_BATCH",
            expected_sequence=expected_sequence,
            command_id=command_id,
            actor=actor,
            payload={},
        )

    async def record_bottle_action_evaluation(
        self,
        *,
        proposal_id: str,
        bottle_id: str,
        expected_sequence: int,
        command_id: str,
        actor: str,
        evaluated_at: datetime,
        waited_seconds: float,
        reaction: str,
        decision: str,
        schema_version: str = "evolving-bottle-evaluation-v1",
    ) -> LabBottleEvent:
        """Append one concise personal reaction to a committed bottle delta.

        The event is bookkeeping evidence only.  It is linked to the exact
        proposal, commit, and addition event, but it does not turn a sequential
        same-bottle observation into controlled causal or population evidence.
        """

        proposal_id = proposal_id.strip()
        bottle_id = bottle_id.strip()
        command_id = command_id.strip()
        actor = actor.strip()
        reaction = reaction.strip()
        decision = decision.strip().upper()
        schema_version = schema_version.strip()
        if not all(
            (proposal_id, bottle_id, command_id, actor, reaction, schema_version)
        ):
            raise ValueError("evaluation identifiers, actor, reaction, and schema must not be empty")
        if decision not in {"CONTINUE", "HOLD", "DILUTE", "STOP", "CANNOT_DETERMINE"}:
            raise ValueError(f"unsupported evolving-bottle evaluation decision: {decision}")
        if evaluated_at.tzinfo is None or evaluated_at.utcoffset() is None:
            raise ValueError("evaluated_at must be timezone-aware")
        waited_seconds = float(waited_seconds)
        if not isfinite(waited_seconds) or waited_seconds < 0:
            raise ValueError("waited_seconds must be finite and nonnegative")
        if expected_sequence < 0:
            raise ValueError("expected_sequence must be nonnegative")

        token = _command_token("evaluate", command_id)
        async with self._transaction():
            proposal = await self.repository.get_bottle_action_proposal(proposal_id)
            if proposal is None:
                raise KeyError(f"Unknown bottle action proposal: {proposal_id}")
            if proposal.bottle_id != bottle_id:
                raise ValueError("evaluation bottle does not match the action proposal")
            commit = await self.repository.bottle_action_commit(proposal_id)
            if commit is None:
                raise ValueError("evaluation requires a committed bottle action")
            payload = {
                "schema": "lab-bottle-action-evaluation-v1",
                "schema_version": schema_version,
                "proposal_id": proposal.id,
                "action_commit_id": commit.id,
                "addition_bottle_event_id": commit.bottle_event_id,
                "actor": actor,
                "evaluated_at": evaluated_at.isoformat(),
                "waited_seconds": waited_seconds,
                "reaction": reaction,
                "decision": decision,
                "evidence_scope": "SEQUENTIAL_PERSONAL_OBSERVATION",
                "controlled_causal_evidence": False,
                "population_generalization_authorized": False,
                "release_authority": False,
                "safety_authority": False,
                "compounding_authority": False,
                "evidence_admission_authorized": False,
                "expected_sequence": expected_sequence,
            }
            existing = await self.repository.event_for_command(bottle_id, token)
            if existing is not None:
                if existing.payload_json != payload:
                    raise IdempotencyConflictError(
                        "evaluation command identifier was already used for a different reaction"
                    )
                return existing
            current_sequence = await self.repository.latest_sequence(bottle_id)
            if current_sequence != expected_sequence:
                raise StaleBottleStreamError(
                    f"expected sequence {expected_sequence}, current sequence is {current_sequence}"
                )
            return await self.repository.add(
                LabBottleEvent(
                    bottle_id=bottle_id,
                    stream_sequence=current_sequence + 1,
                    expected_sequence=expected_sequence,
                    command_id=token,
                    transaction_id=str(uuid4()),
                    event_type="EVALUATE",
                    payload_json=payload,
                )
            )

    async def record_quick_bottle_evaluation(
        self,
        *,
        bottle_id: str,
        addition_event_ids: Sequence[str],
        goal_analysis_sha256: str,
        hypothesis_id: str,
        hypothesis_variant: str,
        expected_sequence: int,
        command_id: str,
        actor: str,
        evaluated_at: datetime,
        waited_seconds: float,
        reaction: str,
        decision: str,
        schema_version: str = "quick-bottle-evaluation-v1",
    ) -> LabBottleEvent:
        """Append a lightweight observation for an exact personal bottle delta.

        This path intentionally does not promote a freeform personal addition
        into planned formula execution.  It only binds the reaction to the
        immutable addition events and the goal-analysis receipt that produced
        the proposal.
        """

        bottle_id = bottle_id.strip()
        command_id = command_id.strip()
        actor = actor.strip()
        reaction = reaction.strip()
        hypothesis_id = hypothesis_id.strip()
        hypothesis_variant = hypothesis_variant.strip()
        schema_version = schema_version.strip()
        decision = decision.strip().upper()
        analysis_hash = _require_sha256(
            goal_analysis_sha256,
            "goal_analysis_sha256",
        )
        event_ids = tuple(str(value).strip() for value in addition_event_ids)
        if not all(
            (
                bottle_id,
                command_id,
                actor,
                reaction,
                hypothesis_id,
                schema_version,
            )
        ):
            raise ValueError("quick-evaluation identifiers and reaction must not be empty")
        if not event_ids or any(not value for value in event_ids):
            raise ValueError("at least one non-empty addition event ID is required")
        if len(event_ids) != len(set(event_ids)):
            raise ValueError("addition event IDs must be unique")
        if hypothesis_variant not in {"low_variant", "high_variant"}:
            raise ValueError(f"unsupported hypothesis variant: {hypothesis_variant}")
        if decision not in {
            "CONTINUE",
            "HOLD",
            "DILUTE",
            "STOP",
            "CANNOT_DETERMINE",
        }:
            raise ValueError(f"unsupported quick-evaluation decision: {decision}")
        if evaluated_at.tzinfo is None or evaluated_at.utcoffset() is None:
            raise ValueError("evaluated_at must be timezone-aware")
        waited_seconds = float(waited_seconds)
        if not isfinite(waited_seconds) or waited_seconds < 0:
            raise ValueError("waited_seconds must be finite and nonnegative")
        if expected_sequence < 0:
            raise ValueError("expected_sequence must be nonnegative")

        token = _command_token("evaluate-personal-delta", command_id)
        payload = {
            "schema": "lab-quick-bottle-evaluation-v1",
            "schema_version": schema_version,
            "addition_event_ids": list(event_ids),
            "goal_analysis_sha256": analysis_hash,
            "hypothesis_id": hypothesis_id,
            "hypothesis_variant": hypothesis_variant,
            "actor": actor,
            "evaluated_at": evaluated_at.isoformat(),
            "waited_seconds": waited_seconds,
            "reaction": reaction,
            "decision": decision,
            "evidence_scope": "SEQUENTIAL_PERSONAL_OBSERVATION",
            "controlled_causal_evidence": False,
            "population_generalization_authorized": False,
            "release_authority": False,
            "safety_authority": False,
            "compounding_authority": False,
            "evidence_admission_authorized": False,
            "expected_sequence": expected_sequence,
        }
        async with self._transaction():
            existing = await self.repository.event_for_command(bottle_id, token)
            if existing is not None:
                if existing.payload_json != payload:
                    raise IdempotencyConflictError(
                        "quick-evaluation command identifier was reused for a different reaction"
                    )
                return existing
            if await self.repository.get_bottle(bottle_id) is None:
                raise KeyError(f"Unknown bottle: {bottle_id}")
            for event_id in event_ids:
                addition = await self.repository.get_event(event_id)
                if addition is None:
                    raise KeyError(f"Unknown bottle addition event: {event_id}")
                if addition.bottle_id != bottle_id or addition.event_type != "ADD_MATERIAL":
                    raise ValueError(
                        "quick evaluation may reference only material additions from the selected bottle"
                    )
                context = addition.payload_json.get("personal_research_context")
                expected_context = {
                    "goal_analysis_sha256": analysis_hash,
                    "hypothesis_id": hypothesis_id,
                    "hypothesis_variant": hypothesis_variant,
                }
                if context != expected_context:
                    raise ValueError(
                        "addition event does not match the selected goal-analysis hypothesis"
                    )
            current_sequence = await self.repository.latest_sequence(bottle_id)
            if current_sequence != expected_sequence:
                raise StaleBottleStreamError(
                    f"expected sequence {expected_sequence}, current sequence is {current_sequence}"
                )
            return await self.repository.add(
                LabBottleEvent(
                    bottle_id=bottle_id,
                    stream_sequence=current_sequence + 1,
                    expected_sequence=expected_sequence,
                    command_id=token,
                    transaction_id=str(uuid4()),
                    event_type="EVALUATE_PERSONAL_DELTA",
                    payload_json=payload,
                )
            )

    async def transfer_between_bottles(
        self,
        *,
        source_bottle_id: str,
        destination_bottle_id: str,
        mass_g: float,
        measured_loss_g: float = 0.0,
        source_expected_sequence: int,
        destination_expected_sequence: int,
        command_id: str,
    ) -> tuple[LabBottleEvent, LabBottleEvent]:
        if source_bottle_id == destination_bottle_id:
            raise ValueError("source and destination bottles must differ")
        if mass_g <= 0:
            raise ValueError("mass_g must be greater than zero")
        if measured_loss_g < 0 or measured_loss_g >= mass_g:
            raise ValueError(
                "measured_loss_g must be nonnegative and less than mass_g"
            )
        source_command = _command_token("transfer-source", command_id)
        destination_command = _command_token("transfer-destination", command_id)
        request_payload = {
            "source_bottle_id": source_bottle_id,
            "destination_bottle_id": destination_bottle_id,
            "mass_g": mass_g,
            "measured_loss_g": measured_loss_g,
            "source_expected_sequence": source_expected_sequence,
            "destination_expected_sequence": destination_expected_sequence,
        }
        async with self._transaction():
            existing_source = await self.repository.event_for_command(
                source_bottle_id, source_command
            )
            existing_destination = await self.repository.event_for_command(
                destination_bottle_id, destination_command
            )
            if existing_source is not None and existing_destination is not None:
                if (
                    existing_source.payload_json != request_payload
                    or existing_destination.payload_json != request_payload
                ):
                    raise IdempotencyConflictError(
                        "command identifier was already used for a different request"
                    )
                return existing_source, existing_destination
            if existing_source is not None or existing_destination is not None:
                raise ConcurrentWriteError("partial transfer command already exists")

            source_bottle = await self.repository.get_bottle(source_bottle_id)
            destination_bottle = await self.repository.get_bottle(destination_bottle_id)
            if source_bottle is None:
                raise KeyError(f"Unknown bottle: {source_bottle_id}")
            if destination_bottle is None:
                raise KeyError(f"Unknown bottle: {destination_bottle_id}")
            if source_bottle.batch_id is not None or destination_bottle.batch_id is not None:
                raise LabTransactionError(
                    "formula/batch-bound bottles cannot use freeform bottle transfers"
                )

            source_sequence = await self.repository.latest_sequence(source_bottle_id)
            destination_sequence = await self.repository.latest_sequence(destination_bottle_id)
            if source_sequence != source_expected_sequence:
                raise StaleBottleStreamError("source bottle stream is stale")
            if destination_sequence != destination_expected_sequence:
                raise StaleBottleStreamError("destination bottle stream is stale")
            if await self.repository.bottle_is_closed(source_bottle_id):
                raise LabTransactionError("source bottle is closed")
            if await self.repository.bottle_is_closed(destination_bottle_id):
                raise LabTransactionError("destination bottle is closed")
            source_state = await self.repository.reconstruct_bottle(source_bottle_id)
            if mass_g > source_state.total_mass_g + 1e-12:
                raise InsufficientBottleMassError("transfer exceeds source bottle mass")

            transaction_id = str(uuid4())
            source_event = await self.repository.add(
                LabBottleEvent(
                    bottle_id=source_bottle_id,
                    stream_sequence=source_sequence + 1,
                    expected_sequence=source_expected_sequence,
                    command_id=source_command,
                    transaction_id=transaction_id,
                    event_type="TRANSFER",
                    payload_json=request_payload,
                )
            )
            destination_event = await self.repository.add(
                LabBottleEvent(
                    bottle_id=destination_bottle_id,
                    stream_sequence=destination_sequence + 1,
                    expected_sequence=destination_expected_sequence,
                    command_id=destination_command,
                    transaction_id=transaction_id,
                    event_type="TRANSFER",
                    payload_json=request_payload,
                )
            )

            transferred_stock_mass = 0.0
            for stock_id, stock_mass in source_state.stock_masses_g.items():
                portion = mass_g * stock_mass / source_state.total_mass_g
                transferred_stock_mass += portion
                stock = await self.repository.get_stock(stock_id)
                material_id = stock.material_id if stock is not None else None
                destination_portion = portion * (
                    (mass_g - measured_loss_g) / mass_g
                )
                await self.repository.add(
                    LabBottleEventEffect(
                        event_id=source_event.id,
                        bottle_id=source_bottle_id,
                        stock_solution_id=stock_id,
                        material_id=material_id,
                        mass_delta_g=-portion,
                    )
                )
                await self.repository.add(
                    LabBottleEventEffect(
                        event_id=destination_event.id,
                        bottle_id=destination_bottle_id,
                        stock_solution_id=stock_id,
                        material_id=material_id,
                        mass_delta_g=destination_portion,
                    )
                )
            unassigned_mass = mass_g - transferred_stock_mass
            if unassigned_mass > 1e-12:
                destination_unassigned = unassigned_mass * (
                    (mass_g - measured_loss_g) / mass_g
                )
                await self.repository.add(
                    LabBottleEventEffect(
                        event_id=source_event.id,
                        bottle_id=source_bottle_id,
                        mass_delta_g=-unassigned_mass,
                    )
                )
                await self.repository.add(
                    LabBottleEventEffect(
                        event_id=destination_event.id,
                        bottle_id=destination_bottle_id,
                        mass_delta_g=destination_unassigned,
                    )
                )
            return source_event, destination_event

    async def compensate_bottle_event(
        self,
        *,
        bottle_id: str,
        event_id: str,
        expected_sequence: int,
        command_id: str,
        actor: str = "system",
    ) -> LabBottleEvent:
        token = _command_token(f"compensate:{event_id}", command_id)
        async with self._transaction():
            existing = await self.repository.event_for_command(bottle_id, token)
            if existing is not None:
                if existing.correction_of_event_id != event_id:
                    raise IdempotencyConflictError(
                        "command identifier was already used for a different request"
                    )
                return existing
            original = await self.repository.get_event(event_id)
            if original is None or original.bottle_id != bottle_id:
                raise KeyError(f"Unknown bottle event: {event_id}")
            if original.event_type in {"compensate", "CORRECT_ENTRY"}:
                raise ValueError("compensating events cannot themselves be compensated")

            originals = (
                await self.repository.events_for_transaction(original.transaction_id)
                if original.event_type
                in {"transfer_out", "transfer_in", "TRANSFER"}
                else [original]
            )
            for item in originals:
                if await self.repository.correction_for_event(item.id) is not None:
                    raise AlreadyCompensatedError(
                        "event transaction is already compensated"
                    )

            current_sequences = {
                item.bottle_id: await self.repository.latest_sequence(item.bottle_id)
                for item in originals
            }
            if current_sequences[bottle_id] != expected_sequence:
                raise StaleBottleStreamError(
                    f"expected sequence {expected_sequence}, current sequence is "
                    f"{current_sequences[bottle_id]}"
                )

            correction_transaction_id = str(uuid4())
            selected_correction: LabBottleEvent | None = None
            for item in originals:
                current_sequence = current_sequences[item.bottle_id]
                correction = await self.repository.add(
                    LabBottleEvent(
                        bottle_id=item.bottle_id,
                        stream_sequence=current_sequence + 1,
                        expected_sequence=current_sequence,
                        command_id=_command_token(f"compensate:{item.id}", command_id),
                        transaction_id=correction_transaction_id,
                        event_type="CORRECT_ENTRY",
                        correction_of_event_id=item.id,
                        payload_json={
                            "correction_of_event_id": item.id,
                            "correction_of_transaction_id": original.transaction_id,
                            "actor": actor,
                        },
                    )
                )
                if item.id == event_id:
                    selected_correction = correction
                await self._reverse_event_effects(
                    item.id,
                    correction,
                    actor=actor,
                )
            assert selected_correction is not None
            return selected_correction

    async def _reverse_event_effects(
        self,
        event_id: str,
        correction: LabBottleEvent,
        *,
        actor: str,
    ) -> None:
        for original_effect in await self.repository.effects_for_event(event_id):
            inverse_effect = await self.repository.add(
                LabBottleEventEffect(
                    event_id=correction.id,
                    bottle_id=original_effect.bottle_id,
                    stock_solution_id=original_effect.stock_solution_id,
                    material_id=original_effect.material_id,
                    mass_delta_g=-original_effect.mass_delta_g,
                    measured_volume_ul=(
                        -original_effect.measured_volume_ul
                        if original_effect.measured_volume_ul is not None
                        else None
                    ),
                    density_g_ml=original_effect.density_g_ml,
                )
            )
            original_movement = await self.repository.inventory_movement_for_effect(
                original_effect.id
            )
            if original_movement is not None:
                stock = await self.repository.get_stock(
                    original_movement.stock_solution_id
                )
                if stock is None:
                    raise KeyError(
                        "Unknown stock solution: "
                        f"{original_movement.stock_solution_id}"
                    )
                before = await self.repository.stock_balance_g(stock.id)
                delta = -original_movement.mass_delta_g
                await self._append_inventory_movement(
                    stock=stock,
                    movement_type="REVERSAL",
                    raw_quantity=abs(delta),
                    balance_before=before,
                    balance_after=before + delta,
                    actor=actor,
                    transaction_id=correction.transaction_id,
                    idempotency_key=f"movement:{correction.id}:{inverse_effect.id}",
                    reason="compensating_event",
                    mass_delta_g=delta,
                    event_effect_id=inverse_effect.id,
                    bottle_event_id=correction.id,
                    reversal_of_movement_id=original_movement.id,
                    measured_volume_ul=(
                        -original_movement.measured_volume_ul
                        if original_movement.measured_volume_ul is not None
                        else None
                    ),
                    standard_uncertainty=(
                        original_movement.standard_uncertainty
                    ),
                )

    async def reconstruct_bottle(self, bottle_id: str) -> BottleLedgerState:
        return await self.repository.reconstruct_bottle(bottle_id)

    async def stock_balance_g(self, stock_solution_id: str) -> float:
        return await self.repository.stock_balance_g(stock_solution_id)

    async def reconcile_stock_balance(
        self,
        stock_solution_id: str,
        remaining_mass_g: float,
        *,
        actor: str = "administrator",
        command_id: str | None = None,
        standard_uncertainty: float | None = None,
    ) -> LabStockSolution:
        """Record an append-only adjustment while keeping the projection synchronized."""

        if remaining_mass_g < 0:
            raise ValueError("remaining_mass_g must be nonnegative")
        async with self._transaction():
            stock = await self.repository.get_stock(stock_solution_id)
            if stock is None:
                raise KeyError(f"Unknown stock solution: {stock_solution_id}")
            current_balance = await self.repository.stock_balance_g(stock_solution_id)
            adjustment = remaining_mass_g - current_balance
            if abs(adjustment) > 1e-12:
                transaction_id = str(uuid4())
                await self._append_inventory_movement(
                    stock=stock,
                    movement_type="ADJUSTMENT",
                    raw_quantity=abs(adjustment),
                    balance_before=current_balance,
                    balance_after=remaining_mass_g,
                    actor=actor,
                    transaction_id=transaction_id,
                    idempotency_key=(
                        f"reconcile:{command_id}"
                        if command_id
                        else f"reconcile:{transaction_id}"
                    ),
                    reason="manual_reconciliation",
                    mass_delta_g=adjustment,
                    admin_cause="manual_reconciliation",
                    standard_uncertainty=standard_uncertainty,
                )
            stock.remaining_mass_g = remaining_mass_g
            return stock

    async def create_experiment(
        self,
        name: str,
        *,
        protocol: dict,
        status: str = "planned",
    ) -> LabExperiment:
        name = name.strip()
        status = status.strip()
        if not name or not status:
            raise ValueError("experiment name and status must not be empty")
        async with self._transaction():
            return await self.repository.add(
                LabExperiment(name=name, protocol_json=dict(protocol), status=status)
            )

    async def add_experiment_sample(
        self,
        *,
        experiment_id: str,
        bottle_id: str,
        blind_code: str,
    ) -> LabSample:
        blind_code = blind_code.strip()
        if not blind_code:
            raise ValueError("blind_code must not be empty")
        async with self._transaction():
            if await self.repository.get_experiment(experiment_id) is None:
                raise KeyError(f"Unknown experiment: {experiment_id}")
            if await self.repository.get_bottle(bottle_id) is None:
                raise KeyError(f"Unknown bottle: {bottle_id}")
            return await self.repository.add(
                LabSample(
                    experiment_id=experiment_id,
                    bottle_id=bottle_id,
                    blind_code=blind_code,
                )
            )

    async def record_application(
        self,
        *,
        sample_id: str,
        applied_at: datetime,
        dose: dict,
        context: dict,
    ) -> LabApplication:
        if applied_at.tzinfo is None or applied_at.utcoffset() is None:
            raise ValueError("applied_at must be timezone-aware")
        async with self._transaction():
            if await self.repository.get_sample(sample_id) is None:
                raise KeyError(f"Unknown sample: {sample_id}")
            return await self.repository.add(
                LabApplication(
                    sample_id=sample_id,
                    applied_at=applied_at,
                    dose_json=dict(dose),
                    context_json=dict(context),
                )
            )

    async def record_observation(
        self,
        *,
        application_id: str,
        elapsed_seconds: float,
        observations: dict,
    ) -> LabObservation:
        if elapsed_seconds < 0:
            raise ValueError("elapsed_seconds must be nonnegative")
        async with self._transaction():
            if await self.repository.get_application(application_id) is None:
                raise KeyError(f"Unknown application: {application_id}")
            return await self.repository.add(
                LabObservation(
                    application_id=application_id,
                    elapsed_seconds=elapsed_seconds,
                    observations_json=dict(observations),
                )
            )

    async def record_pairwise_comparison(
        self,
        *,
        experiment_id: str,
        left_sample_id: str,
        right_sample_id: str,
        preferred_sample_id: str | None,
        context: dict,
    ) -> LabPairwiseComparison:
        if left_sample_id == right_sample_id:
            raise ValueError("pairwise comparison requires different samples")
        if preferred_sample_id not in {None, left_sample_id, right_sample_id}:
            raise ValueError("preferred sample must be left, right, or None for a tie")
        async with self._transaction():
            if await self.repository.get_experiment(experiment_id) is None:
                raise KeyError(f"Unknown experiment: {experiment_id}")
            left = await self.repository.get_sample(left_sample_id)
            right = await self.repository.get_sample(right_sample_id)
            if left is None or right is None:
                raise KeyError("Unknown comparison sample")
            if left.experiment_id != experiment_id or right.experiment_id != experiment_id:
                raise ValueError("comparison samples must belong to the same experiment")
            return await self.repository.add(
                LabPairwiseComparison(
                    experiment_id=experiment_id,
                    left_sample_id=left_sample_id,
                    right_sample_id=right_sample_id,
                    preferred_sample_id=preferred_sample_id,
                    context_json=dict(context),
                )
            )

    async def record_prediction(
        self,
        *,
        experiment_id: str,
        sample_id: str | None,
        model_key: str,
        model_version: str,
        status: str,
        prediction: dict,
        evidence_id: str | None = None,
    ) -> LabPrediction:
        if not model_key.strip() or not model_version.strip() or not status.strip():
            raise ValueError("prediction model key, version, and status must not be empty")
        async with self._transaction():
            if await self.repository.get_experiment(experiment_id) is None:
                raise KeyError(f"Unknown experiment: {experiment_id}")
            if sample_id is not None:
                sample = await self.repository.get_sample(sample_id)
                if sample is None or sample.experiment_id != experiment_id:
                    raise ValueError("prediction sample must belong to the experiment")
            return await self.repository.add(
                LabPrediction(
                    experiment_id=experiment_id,
                    sample_id=sample_id,
                    model_key=model_key.strip(),
                    model_version=model_version.strip(),
                    status=status.strip(),
                    prediction_json=dict(prediction),
                    evidence_id=evidence_id,
                )
            )

    async def record_outcome(
        self,
        *,
        experiment_id: str,
        prediction_id: str | None,
        outcome: dict,
    ) -> LabOutcome:
        async with self._transaction():
            if await self.repository.get_experiment(experiment_id) is None:
                raise KeyError(f"Unknown experiment: {experiment_id}")
            if prediction_id is not None:
                prediction = await self.repository.get_prediction(prediction_id)
                if prediction is None or prediction.experiment_id != experiment_id:
                    raise ValueError("outcome prediction must belong to the experiment")
            return await self.repository.add(
                LabOutcome(
                    experiment_id=experiment_id,
                    prediction_id=prediction_id,
                    outcome_json=dict(outcome),
                )
            )


__all__ = [
    "AlreadyCompensatedError",
    "ConcurrentWriteError",
    "IdempotencyConflictError",
    "InsufficientBottleMassError",
    "InsufficientStockError",
    "LabService",
    "LabTransactionError",
    "StaleBottleStreamError",
]


def _command_token(scope: str, command_id: str) -> str:
    command = command_id.strip()
    if not command:
        raise ValueError("command_id must not be empty")
    return sha256(f"{scope}\0{command}".encode("utf-8")).hexdigest()
