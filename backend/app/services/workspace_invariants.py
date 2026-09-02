"""Fail-closed cross-table invariants replayed before workspace import commits."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, InvalidOperation
from math import isclose

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lab import (
    LabBottle,
    LabBottleEvent,
    LabBottleMeasurement,
    LabInventoryMovement,
    LabStockSolution,
)
from app.models.lab_execution import (
    LabBottleActionCommit,
    LabBottleActionConfirmation,
    LabBottleActionProposal,
)
from app.models.lab_planning import (
    LabAcceptedTargetVersion,
    LabBuildPlanLine,
    LabBuildPlanVersion,
    LabInventoryMappingVersion,
    LabInventoryReservationEvent,
    LabTargetHypothesisVersion,
    LabTargetLine,
)
from app.services.inventory_authority import is_current_inventory_snapshot_ref
from app.services.stock_lineage import StockLineageError, validate_workspace_stock_lineage
from app.services.stock_strength_quarantine import (
    StockStrengthQuarantineError,
    quarantine_record_for_product_key,
)


class WorkspaceInvariantError(ValueError):
    """Stable rejection when imported workspace bytes violate physical authority."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


_ALLOWED_STOCK_FRACTION_BASES = frozenset(
    {"mass_fraction", "volume_fraction", "amount_fraction"}
)
_EXECUTABLE_PLAN_STATUSES = frozenset(
    {"APPROVED", "RESERVED", "EXECUTING", "CLOSED"}
)


def _decimal(value: object, *, code: str, field: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as error:
        raise WorkspaceInvariantError(
            code,
            f"{field} must be a finite decimal quantity.",
        ) from error
    if not result.is_finite():
        raise WorkspaceInvariantError(
            code,
            f"{field} must be a finite decimal quantity.",
        )
    return result


def _canonical_decimal_text(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if text in {"", "-0"}:
        return "0"
    return text


async def _validate_stock_solutions(
    session: AsyncSession,
    *,
    require_exact_stock_decimal: bool,
) -> None:
    stocks = list(
        (
            await session.execute(
                select(LabStockSolution).order_by(
                    LabStockSolution.created_at,
                    LabStockSolution.id,
                )
            )
        ).scalars()
    )
    for stock in stocks:
        projection = _decimal(
            stock.active_fraction,
            code="STOCK_ACTIVE_FRACTION_INVALID",
            field=f"Stock {stock.id} active_fraction",
        )
        exact_text = stock.active_fraction_decimal_text
        if exact_text is None:
            if require_exact_stock_decimal:
                raise WorkspaceInvariantError(
                    "STOCK_ACTIVE_FRACTION_EXACT_AUTHORITY_MISSING",
                    f"Stock {stock.id} lacks exact active-fraction decimal authority.",
                )
            active_fraction = projection
        else:
            active_fraction = _decimal(
                exact_text,
                code="STOCK_ACTIVE_FRACTION_INVALID",
                field=f"Stock {stock.id} exact active fraction",
            )
            if _canonical_decimal_text(active_fraction) != exact_text:
                raise WorkspaceInvariantError(
                    "STOCK_ACTIVE_FRACTION_INVALID",
                    f"Stock {stock.id} exact active-fraction text is not canonical.",
                )
            if float(active_fraction) != float(projection):
                raise WorkspaceInvariantError(
                    "STOCK_ACTIVE_FRACTION_PROJECTION_MISMATCH",
                    f"Stock {stock.id} exact active fraction disagrees with its float projection.",
                )
        if not Decimal("0") < active_fraction <= Decimal("1"):
            raise WorkspaceInvariantError(
                "STOCK_ACTIVE_FRACTION_OUT_OF_RANGE",
                f"Stock {stock.id} active fraction must be in (0, 1].",
            )
        if stock.fraction_basis not in _ALLOWED_STOCK_FRACTION_BASES:
            raise WorkspaceInvariantError(
                "STOCK_FRACTION_BASIS_INVALID",
                f"Stock {stock.id} uses an unsupported concentration basis.",
            )
        initial_mass = _decimal(
            stock.initial_mass_g,
            code="STOCK_MASS_DOMAIN_INVALID",
            field=f"Stock {stock.id} initial_mass_g",
        )
        if initial_mass < 0:
            raise WorkspaceInvariantError(
                "STOCK_MASS_DOMAIN_INVALID",
                f"Stock {stock.id} initial mass must be nonnegative.",
            )
        if stock.remaining_mass_g is not None:
            remaining_mass = _decimal(
                stock.remaining_mass_g,
                code="STOCK_MASS_DOMAIN_INVALID",
                field=f"Stock {stock.id} remaining_mass_g",
            )
            if remaining_mass < 0 or remaining_mass > initial_mass:
                raise WorkspaceInvariantError(
                    "STOCK_MASS_DOMAIN_INVALID",
                    f"Stock {stock.id} remaining mass is outside its physical stock domain.",
                )
        if stock.density_g_ml is not None:
            density = _decimal(
                stock.density_g_ml,
                code="STOCK_DENSITY_DOMAIN_INVALID",
                field=f"Stock {stock.id} density_g_ml",
            )
            if density <= 0:
                raise WorkspaceInvariantError(
                    "STOCK_DENSITY_DOMAIN_INVALID",
                    f"Stock {stock.id} density must be greater than zero.",
                )


async def _validate_inventory_ledger(session: AsyncSession) -> None:
    stocks = list(
        (
            await session.execute(
                select(LabStockSolution).order_by(LabStockSolution.id)
            )
        ).scalars()
    )
    movements = list(
        (
            await session.execute(
                select(LabInventoryMovement).order_by(
                    LabInventoryMovement.created_at,
                    LabInventoryMovement.id,
                )
            )
        ).scalars()
    )
    reservation_events = list(
        (
            await session.execute(
                select(LabInventoryReservationEvent).order_by(
                    LabInventoryReservationEvent.reservation_id,
                    LabInventoryReservationEvent.sequence,
                    LabInventoryReservationEvent.id,
                )
            )
        ).scalars()
    )
    movements_by_stock: dict[str, list[LabInventoryMovement]] = defaultdict(list)
    for movement in movements:
        movements_by_stock[movement.stock_solution_id].append(movement)

    final_balance_by_stock: dict[str, float] = {}
    for stock in stocks:
        balance = float(stock.initial_mass_g)
        for movement in movements_by_stock.get(stock.id, []):
            if str(movement.unit).strip().lower() not in {"g", "gram", "grams"}:
                raise WorkspaceInvariantError(
                    "INVENTORY_MOVEMENT_UNIT_INVALID",
                    f"Inventory movement {movement.id} is outside the mass-ledger unit contract.",
                )
            expected_active = float(movement.raw_quantity) * float(
                stock.active_fraction
            )
            if not isclose(
                float(movement.active_quantity),
                expected_active,
                rel_tol=1e-9,
                abs_tol=1e-12,
            ):
                raise WorkspaceInvariantError(
                    "INVENTORY_MOVEMENT_ACTIVE_ARITHMETIC_MISMATCH",
                    f"Inventory movement {movement.id} active quantity is inconsistent with its exact stock fraction.",
                )
            if not isclose(
                float(movement.balance_before),
                balance,
                rel_tol=1e-12,
                abs_tol=1e-12,
            ):
                raise WorkspaceInvariantError(
                    "INVENTORY_MOVEMENT_BALANCE_MISMATCH",
                    f"Inventory movement {movement.id} does not continue the immutable stock balance chain.",
                )
            expected_after = balance + float(movement.mass_delta_g)
            if not isclose(
                float(movement.balance_after),
                expected_after,
                rel_tol=1e-12,
                abs_tol=1e-12,
            ) or expected_after < -1e-12:
                raise WorkspaceInvariantError(
                    "INVENTORY_MOVEMENT_BALANCE_MISMATCH",
                    f"Inventory movement {movement.id} has inconsistent or negative post-movement balance.",
                )
            balance = expected_after
        final_balance_by_stock[stock.id] = balance

    latest_reservation_by_id: dict[str, LabInventoryReservationEvent] = {}
    for event in reservation_events:
        latest_reservation_by_id[event.reservation_id] = event
    active_reserved_by_stock: dict[str, float] = defaultdict(float)
    for event in latest_reservation_by_id.values():
        if event.state == "RESERVED":
            active_reserved_by_stock[event.stock_solution_id] += float(
                event.reserved_mass_g
            )
    for stock_id, reserved_mass in active_reserved_by_stock.items():
        reserved_stock_balance = final_balance_by_stock.get(stock_id)
        if reserved_stock_balance is None:
            raise WorkspaceInvariantError(
                "STOCK_SOLUTION_NOT_FOUND",
                f"Active reservations reference missing stock solution {stock_id}.",
            )
        if reserved_mass > reserved_stock_balance + 1e-12:
            raise WorkspaceInvariantError(
                "ACTIVE_RESERVATIONS_EXCEED_STOCK_BALANCE",
                f"Active reservations for stock {stock_id} exceed its canonical physical balance.",
            )


def _line_target_mass_g(line: LabBuildPlanLine) -> float:
    unit = str(line.unit).strip().lower().replace("μ", "µ")
    if unit in {"g", "gram", "grams"}:
        return float(line.planned_raw_quantity)
    if unit in {"ul", "µl"}:
        if line.density_g_ml is None:
            raise WorkspaceInvariantError(
                "BUILD_LINE_MASS_AUTHORITY_UNAVAILABLE",
                f"Build line {line.id} has volume quantity without authoritative density.",
            )
        return (float(line.planned_raw_quantity) / 1000.0) * float(line.density_g_ml)
    raise WorkspaceInvariantError(
        "BUILD_LINE_MASS_AUTHORITY_UNAVAILABLE",
        f"Build line {line.id} unit cannot be converted to an immutable mass ceiling.",
    )


async def _validate_build_plans(session: AsyncSession) -> None:
    plans = list(
        (
            await session.execute(
                select(LabBuildPlanVersion).order_by(
                    LabBuildPlanVersion.plan_id,
                    LabBuildPlanVersion.version_number,
                    LabBuildPlanVersion.id,
                )
            )
        ).scalars()
    )
    targets = list(
        (
            await session.execute(
                select(LabTargetHypothesisVersion).order_by(
                    LabTargetHypothesisVersion.target_id,
                    LabTargetHypothesisVersion.version_number,
                    LabTargetHypothesisVersion.id,
                )
            )
        ).scalars()
    )
    acceptances = list(
        (
            await session.execute(
                select(LabAcceptedTargetVersion).order_by(
                    LabAcceptedTargetVersion.accepted_target_id,
                    LabAcceptedTargetVersion.version_number,
                    LabAcceptedTargetVersion.id,
                )
            )
        ).scalars()
    )
    mappings = list(
        (
            await session.execute(
                select(LabInventoryMappingVersion).order_by(
                    LabInventoryMappingVersion.mapping_id,
                    LabInventoryMappingVersion.version_number,
                    LabInventoryMappingVersion.id,
                )
            )
        ).scalars()
    )
    lines = list(
        (
            await session.execute(
                select(LabBuildPlanLine).order_by(
                    LabBuildPlanLine.build_plan_version_id,
                    LabBuildPlanLine.position,
                    LabBuildPlanLine.id,
                )
            )
        ).scalars()
    )
    plan_by_id = {plan.id: plan for plan in plans}
    target_by_id = {target.id: target for target in targets}
    acceptance_by_id = {acceptance.id: acceptance for acceptance in acceptances}
    mapping_by_id = {mapping.id: mapping for mapping in mappings}
    latest_plan_by_key: dict[str, LabBuildPlanVersion] = {}
    latest_target_by_key: dict[str, LabTargetHypothesisVersion] = {}
    latest_mapping_by_key: dict[str, LabInventoryMappingVersion] = {}
    for plan_version in plans:
        latest_plan_by_key[plan_version.plan_id] = plan_version
    for target_version in targets:
        latest_target_by_key[target_version.target_id] = target_version
    for mapping_version in mappings:
        latest_mapping_by_key[mapping_version.mapping_id] = mapping_version

    for plan in plans:
        if not is_current_inventory_snapshot_ref(plan.inventory_snapshot_ref):
            raise WorkspaceInvariantError(
                "INVENTORY_AUTHORITY_MISMATCH",
                f"Build plan {plan.id} is not pinned to the exact current V5 inventory authority.",
            )
        plan_target = target_by_id.get(plan.target_hypothesis_version_id)
        if plan_target is None:
            raise WorkspaceInvariantError(
                "TARGET_NOT_FOUND",
                f"Build plan {plan.id} references a missing target hypothesis.",
            )
        acceptance = acceptance_by_id.get(plan.accepted_target_version_id)
        if (
            acceptance is None
            or acceptance.target_hypothesis_version_id != plan_target.id
        ):
            raise WorkspaceInvariantError(
                "BUILD_PLAN_ACCEPTED_TARGET_MISMATCH",
                f"Build plan {plan.id} lacks matching immutable target acceptance.",
            )
        if plan.status in _EXECUTABLE_PLAN_STATUSES:
            try:
                quarantine = quarantine_record_for_product_key(
                    plan_target.product_key
                )
            except StockStrengthQuarantineError as error:
                raise WorkspaceInvariantError(error.code, str(error)) from error
            if quarantine is not None:
                raise WorkspaceInvariantError(
                    "STOCK_STRENGTH_RECALC_QUARANTINE",
                    f"Executable build plan {plan.id} targets a V5 stock-strength recalculation quarantine entry without a valid clearance receipt.",
                )
        if (
            latest_plan_by_key.get(plan.plan_id) is plan
            and plan.status in _EXECUTABLE_PLAN_STATUSES
            and latest_target_by_key.get(plan_target.target_id) is not plan_target
        ):
            raise WorkspaceInvariantError(
                "STALE_TARGET_HYPOTHESIS_VERSION",
                f"Executable build plan {plan.id} references a superseded target hypothesis.",
            )

    for line in lines:
        stock = await session.get(LabStockSolution, line.stock_solution_id)
        line_mapping = mapping_by_id.get(line.inventory_mapping_version_id)
        target_line = await session.get(LabTargetLine, line.target_line_id)
        line_plan = plan_by_id.get(line.build_plan_version_id)
        if (
            stock is None
            or line_mapping is None
            or target_line is None
            or line_plan is None
        ):
            raise WorkspaceInvariantError(
                "BUILD_PLAN_AUTHORITY_REFERENCE_MISSING",
                f"Build line {line.id} references missing stock, mapping, or target authority.",
            )
        if (
            line_mapping.stock_solution_id != line.stock_solution_id
            or line_mapping.target_line_id != line.target_line_id
        ):
            raise WorkspaceInvariantError(
                "BUILD_LINE_MAPPING_MISMATCH",
                f"Build line {line.id} does not use its mapping's exact stock solution.",
            )
        if (
            target_line.target_hypothesis_version_id
            != line_plan.target_hypothesis_version_id
        ):
            raise WorkspaceInvariantError(
                "BUILD_LINE_TARGET_VERSION_MISMATCH",
                f"Build line {line.id} does not belong to its plan's immutable target version.",
            )
        if (
            latest_plan_by_key.get(line_plan.plan_id) is line_plan
            and line_plan.status in _EXECUTABLE_PLAN_STATUSES
            and latest_mapping_by_key.get(line_mapping.mapping_id)
            is not line_mapping
        ):
            raise WorkspaceInvariantError(
                "STALE_INVENTORY_MAPPING_VERSION",
                f"Executable build line {line.id} references a superseded inventory mapping.",
            )
        if not isclose(
            float(line.concentration_fraction),
            float(stock.active_fraction),
            rel_tol=1e-12,
            abs_tol=1e-12,
        ):
            raise WorkspaceInvariantError(
                "BUILD_LINE_STOCK_FRACTION_MISMATCH",
                f"Build line {line.id} concentration fraction differs from its exact stock solution.",
            )
        if line.concentration_basis != stock.fraction_basis:
            raise WorkspaceInvariantError(
                "BUILD_LINE_STOCK_BASIS_MISMATCH",
                f"Build line {line.id} concentration basis differs from its exact stock solution.",
            )
        if not isclose(
            float(line.planned_active_quantity),
            float(line.planned_raw_quantity) * float(line.concentration_fraction),
            rel_tol=1e-9,
            abs_tol=1e-12,
        ):
            raise WorkspaceInvariantError(
                "BUILD_LINE_ACTIVE_ARITHMETIC_MISMATCH",
                f"Build line {line.id} active quantity is inconsistent with raw quantity and stock fraction.",
            )
        if line_mapping.identity_status == "EXACT":
            if line.unit != target_line.unit:
                raise WorkspaceInvariantError(
                    "EXACT_MAPPING_QUANTITY_BASIS_MISMATCH",
                    f"Exact build line {line.id} changed the immutable target active-quantity unit.",
                )
            if not isclose(
                float(line.planned_active_quantity),
                float(target_line.target_active_quantity),
                rel_tol=1e-9,
                abs_tol=1e-12,
            ):
                raise WorkspaceInvariantError(
                    "EXACT_MAPPING_ACTIVE_QUANTITY_MISMATCH",
                    f"Exact build line {line.id} changed the immutable target active quantity.",
                )


async def _validate_reservations_and_commits(session: AsyncSession) -> None:
    reservations = list(
        (
            await session.execute(
                select(LabInventoryReservationEvent).order_by(
                    LabInventoryReservationEvent.reservation_id,
                    LabInventoryReservationEvent.sequence,
                    LabInventoryReservationEvent.id,
                )
            )
        ).scalars()
    )
    reservation_chains: dict[str, list[LabInventoryReservationEvent]] = (
        defaultdict(list)
    )
    for reservation in reservations:
        reservation_chains[reservation.reservation_id].append(reservation)
    for reservation_id, chain in reservation_chains.items():
        for index, event in enumerate(chain, start=1):
            if event.sequence != index:
                raise WorkspaceInvariantError(
                    "RESERVATION_SEQUENCE_INVALID",
                    f"Reservation {reservation_id} has a non-contiguous event sequence.",
                )
            if index == 1:
                if event.parent_event_id is not None or event.state != "RESERVED":
                    raise WorkspaceInvariantError(
                        "RESERVATION_SEQUENCE_INVALID",
                        f"Reservation {reservation_id} lacks a valid initial RESERVED event.",
                    )
                continue
            parent = chain[index - 2]
            if event.parent_event_id != parent.id:
                raise WorkspaceInvariantError(
                    "RESERVATION_SEQUENCE_INVALID",
                    f"Reservation {reservation_id} event {event.id} breaks its immutable parent chain.",
                )
            if (
                event.build_plan_version_id != parent.build_plan_version_id
                or event.build_plan_line_id != parent.build_plan_line_id
                or event.stock_solution_id != parent.stock_solution_id
                or not isclose(
                    float(event.reserved_mass_g),
                    float(parent.reserved_mass_g),
                    rel_tol=0.0,
                    abs_tol=1e-12,
                )
            ):
                raise WorkspaceInvariantError(
                    "RESERVATION_AUTHORITY_MUTATED",
                    f"Reservation {reservation_id} changed immutable line, stock, or quantity authority.",
                )
    for reservation in reservations:
        plan = await session.get(
            LabBuildPlanVersion,
            reservation.build_plan_version_id,
        )
        if plan is None or plan.status != "APPROVED":
            raise WorkspaceInvariantError(
                "RESERVATION_REQUIRES_APPROVED_BUILD_PLAN",
                f"Reservation {reservation.id} is not bound to an approved build plan.",
            )
        line = await session.get(LabBuildPlanLine, reservation.build_plan_line_id)
        if line is None:
            raise WorkspaceInvariantError(
                "BUILD_PLAN_LINE_NOT_FOUND",
                f"Reservation {reservation.id} references a missing build-plan line.",
            )
        if line.build_plan_version_id != plan.id:
            raise WorkspaceInvariantError(
                "BUILD_PLAN_LINE_MISMATCH",
                f"Reservation {reservation.id} line does not belong to its approved plan version.",
            )
        if reservation.stock_solution_id != line.stock_solution_id:
            raise WorkspaceInvariantError(
                "RESERVATION_STOCK_MISMATCH",
                f"Reservation {reservation.id} changed the immutable build-line stock.",
            )
        if float(reservation.reserved_mass_g) > _line_target_mass_g(line) + 1e-12:
            raise WorkspaceInvariantError(
                "RESERVATION_EXCEEDS_BUILD_LINE_TARGET",
                f"Reservation {reservation.id} exceeds the immutable build-line mass target.",
            )

    movements = list(
        (
            await session.execute(
                select(LabInventoryMovement)
                .where(LabInventoryMovement.movement_type == "CONSUMPTION")
                .order_by(LabInventoryMovement.created_at, LabInventoryMovement.id)
            )
        ).scalars()
    )
    cumulative: dict[str, float] = defaultdict(float)
    for movement in movements:
        stock = await session.get(LabStockSolution, movement.stock_solution_id)
        if stock is None:
            raise WorkspaceInvariantError(
                "STOCK_SOLUTION_NOT_FOUND",
                f"Consumption movement {movement.id} references a missing stock solution.",
            )
        if stock.fraction_basis != "mass_fraction":
            raise WorkspaceInvariantError(
                "PHYSICAL_ACTIVE_EQUIVALENT_BASIS_UNSUPPORTED",
                f"Consumption movement {movement.id} uses mass arithmetic on non-mass-fraction stock authority.",
            )
        if movement.build_plan_line_id is None:
            continue
        line = await session.get(LabBuildPlanLine, movement.build_plan_line_id)
        if line is None:
            raise WorkspaceInvariantError(
                "BUILD_PLAN_LINE_NOT_FOUND",
                f"Consumption movement {movement.id} references a missing build-plan line.",
            )
        if movement.stock_solution_id != line.stock_solution_id:
            raise WorkspaceInvariantError(
                "COMMIT_STOCK_MISMATCH",
                f"Consumption movement {movement.id} changed the immutable build-line stock.",
            )
        if movement.reservation_event_id is None:
            raise WorkspaceInvariantError(
                "COMMIT_RESERVATION_AUTHORITY_MISSING",
                f"Consumption movement {movement.id} with build-line authority lacks a reservation event.",
            )
        movement_reservation = await session.get(
            LabInventoryReservationEvent,
            movement.reservation_event_id,
        )
        if movement_reservation is None:
            raise WorkspaceInvariantError(
                "COMMIT_RESERVATION_AUTHORITY_MISSING",
                f"Consumption movement {movement.id} references a missing reservation event.",
            )
        if (
            movement_reservation.build_plan_line_id != line.id
            or movement_reservation.stock_solution_id != line.stock_solution_id
        ):
            raise WorkspaceInvariantError(
                "COMMIT_RESERVATION_AUTHORITY_MISMATCH",
                f"Consumption movement {movement.id} reservation does not authorize its immutable line and stock.",
            )
        cumulative[line.id] += float(movement.raw_quantity)
        if float(movement.raw_quantity) > _line_target_mass_g(line) + 1e-12:
            raise WorkspaceInvariantError(
                "MEASUREMENT_EXCEEDS_BUILD_LINE_TARGET",
                f"Consumption movement {movement.id} independently exceeds its build-line target.",
            )
        if cumulative[line.id] > _line_target_mass_g(line) + 1e-12:
            raise WorkspaceInvariantError(
                "CUMULATIVE_COMMIT_EXCEEDS_BUILD_LINE_TARGET",
                f"Committed consumption for build line {line.id} exceeds its immutable target.",
            )


async def _validate_execution_chain(session: AsyncSession) -> None:
    proposals = list(
        (
            await session.execute(
                select(LabBottleActionProposal).order_by(
                    LabBottleActionProposal.created_at,
                    LabBottleActionProposal.id,
                )
            )
        ).scalars()
    )
    confirmations = list(
        (
            await session.execute(
                select(LabBottleActionConfirmation).order_by(
                    LabBottleActionConfirmation.created_at,
                    LabBottleActionConfirmation.id,
                )
            )
        ).scalars()
    )
    measurements = list(
        (
            await session.execute(
                select(LabBottleMeasurement)
                .where(LabBottleMeasurement.proposal_id.is_not(None))
                .order_by(LabBottleMeasurement.created_at, LabBottleMeasurement.id)
            )
        ).scalars()
    )
    commits = list(
        (
            await session.execute(
                select(LabBottleActionCommit).order_by(
                    LabBottleActionCommit.created_at,
                    LabBottleActionCommit.id,
                )
            )
        ).scalars()
    )
    reservation_events = list(
        (
            await session.execute(
                select(LabInventoryReservationEvent).order_by(
                    LabInventoryReservationEvent.reservation_id,
                    LabInventoryReservationEvent.sequence,
                    LabInventoryReservationEvent.id,
                )
            )
        ).scalars()
    )
    bottle_events = list(
        (
            await session.execute(
                select(LabBottleEvent).order_by(
                    LabBottleEvent.bottle_id,
                    LabBottleEvent.stream_sequence,
                    LabBottleEvent.id,
                )
            )
        ).scalars()
    )
    movements = list(
        (
            await session.execute(
                select(LabInventoryMovement).order_by(
                    LabInventoryMovement.created_at,
                    LabInventoryMovement.id,
                )
            )
        ).scalars()
    )

    reservation_by_event_id = {event.id: event for event in reservation_events}
    confirmation_by_proposal = {
        confirmation.proposal_id: confirmation for confirmation in confirmations
    }
    measurements_by_proposal: dict[str, list[LabBottleMeasurement]] = defaultdict(
        list
    )
    for measurement in measurements:
        if measurement.proposal_id is not None:
            measurements_by_proposal[measurement.proposal_id].append(measurement)
    commit_by_proposal = {commit.proposal_id: commit for commit in commits}
    commit_by_fulfilled_event = {
        commit.fulfilled_reservation_event_id: commit for commit in commits
    }
    commit_by_bottle_event = {commit.bottle_event_id: commit for commit in commits}
    bottle_event_by_id = {event.id: event for event in bottle_events}
    movements_by_bottle_event: dict[str, list[LabInventoryMovement]] = defaultdict(
        list
    )
    for movement in movements:
        if movement.bottle_event_id is not None:
            movements_by_bottle_event[movement.bottle_event_id].append(movement)

    for proposal in proposals:
        reservation = reservation_by_event_id.get(proposal.reservation_event_id)
        if (
            reservation is None
            or reservation.reservation_id != proposal.reservation_id
            or reservation.state != "RESERVED"
        ):
            raise WorkspaceInvariantError(
                "ACTION_RESERVATION_AUTHORITY_MISMATCH",
                f"Action proposal {proposal.id} is not bound to its immutable RESERVED event.",
            )
        line = await session.get(LabBuildPlanLine, reservation.build_plan_line_id)
        if line is None:
            raise WorkspaceInvariantError(
                "BUILD_PLAN_LINE_NOT_FOUND",
                f"Action proposal {proposal.id} references a missing build-plan line.",
            )
        if proposal.stock_solution_id != reservation.stock_solution_id:
            raise WorkspaceInvariantError(
                "ACTION_STOCK_MISMATCH",
                f"Action proposal {proposal.id} changed the reserved stock identity.",
            )
        if (
            float(proposal.planned_mass_g) > float(reservation.reserved_mass_g) + 1e-12
            or float(proposal.planned_mass_g) > _line_target_mass_g(line) + 1e-12
        ):
            raise WorkspaceInvariantError(
                "ACTION_EXCEEDS_AUTHORIZED_QUANTITY",
                f"Action proposal {proposal.id} exceeds its reservation or build-line ceiling.",
            )
        if await session.get(LabBottle, proposal.bottle_id) is None:
            raise WorkspaceInvariantError(
                "BOTTLE_NOT_FOUND",
                f"Action proposal {proposal.id} references a missing bottle.",
            )

        confirmation = confirmation_by_proposal.get(proposal.id)
        proposal_measurements = measurements_by_proposal.get(proposal.id, [])
        commit = commit_by_proposal.get(proposal.id)
        if confirmation is not None and confirmation.decision == "REJECTED":
            if proposal_measurements or commit is not None:
                raise WorkspaceInvariantError(
                    "REJECTED_ACTION_HAS_EXECUTION_EVIDENCE",
                    f"Rejected action proposal {proposal.id} has measurement or commit evidence.",
                )
            continue
        if (proposal_measurements or commit is not None) and (
            confirmation is None or confirmation.decision != "CONFIRMED"
        ):
            raise WorkspaceInvariantError(
                "ACTION_CONFIRMATION_REQUIRED",
                f"Action proposal {proposal.id} has execution evidence without affirmative confirmation.",
            )

        mass_measurement: LabBottleMeasurement | None = None
        for measurement in proposal_measurements:
            value = _decimal(
                measurement.value,
                code="ACTION_MEASUREMENT_INVALID",
                field=f"Action measurement {measurement.id} value",
            )
            if value <= 0:
                raise WorkspaceInvariantError(
                    "ACTION_MEASUREMENT_INVALID",
                    f"Action measurement {measurement.id} must be greater than zero.",
                )
            if measurement.quantity_kind != "mass":
                continue
            if mass_measurement is not None:
                raise WorkspaceInvariantError(
                    "ACTION_MASS_MEASUREMENT_AMBIGUOUS",
                    f"Action proposal {proposal.id} has multiple mass measurements.",
                )
            mass_measurement = measurement
            if str(measurement.unit).strip().lower() not in {"g", "gram", "grams"}:
                raise WorkspaceInvariantError(
                    "ACTION_MASS_MEASUREMENT_UNIT_INVALID",
                    f"Action proposal {proposal.id} mass measurement is not in grams.",
                )
            if (
                float(measurement.value) > float(proposal.planned_mass_g) + 1e-12
                or float(measurement.value)
                > float(reservation.reserved_mass_g) + 1e-12
                or float(measurement.value) > _line_target_mass_g(line) + 1e-12
            ):
                raise WorkspaceInvariantError(
                    "ACTION_MEASUREMENT_EXCEEDS_AUTHORITY",
                    f"Action proposal {proposal.id} measurement exceeds proposal, reservation, or line authority.",
                )
        if commit is None:
            continue
        if mass_measurement is None:
            raise WorkspaceInvariantError(
                "ACTION_MEASUREMENT_REQUIRED",
                f"Committed action proposal {proposal.id} lacks a gravimetric measurement.",
            )

        fulfilled = reservation_by_event_id.get(
            commit.fulfilled_reservation_event_id
        )
        if (
            fulfilled is None
            or fulfilled.reservation_id != reservation.reservation_id
            or fulfilled.parent_event_id != reservation.id
            or fulfilled.sequence != reservation.sequence + 1
            or fulfilled.state != "FULFILLED"
        ):
            raise WorkspaceInvariantError(
                "ACTION_FULFILLMENT_AUTHORITY_MISMATCH",
                f"Action commit {commit.id} lacks its exact terminal reservation receipt.",
            )
        event = bottle_event_by_id.get(commit.bottle_event_id)
        expected_event_type = (
            "ADD_SOLVENT"
            if proposal.action_type == "ADD_SOLVENT"
            else "ADD_MATERIAL"
        )
        if (
            event is None
            or event.bottle_id != proposal.bottle_id
            or event.event_type != expected_event_type
            or event.expected_sequence != proposal.expected_sequence
            or event.stream_sequence != proposal.expected_sequence + 1
        ):
            raise WorkspaceInvariantError(
                "ACTION_BOTTLE_EVENT_MISMATCH",
                f"Action commit {commit.id} is not bound to the exact proposed bottle event.",
            )
        event_movements = movements_by_bottle_event.get(event.id, [])
        if len(event_movements) != 1:
            raise WorkspaceInvariantError(
                "ACTION_INVENTORY_MOVEMENT_MISMATCH",
                f"Action commit {commit.id} must have exactly one inventory movement.",
            )
        movement = event_movements[0]
        stock = await session.get(LabStockSolution, proposal.stock_solution_id)
        if stock is None:
            raise WorkspaceInvariantError(
                "STOCK_SOLUTION_NOT_FOUND",
                f"Action proposal {proposal.id} references a missing stock solution.",
            )
        if (
            movement.movement_type != "CONSUMPTION"
            or movement.stock_solution_id != proposal.stock_solution_id
            or movement.build_plan_line_id != line.id
            or movement.reservation_event_id != reservation.id
            or not isclose(
                float(movement.raw_quantity),
                float(mass_measurement.value),
                rel_tol=1e-12,
                abs_tol=1e-12,
            )
            or not isclose(
                float(movement.active_quantity),
                float(mass_measurement.value) * float(stock.active_fraction),
                rel_tol=1e-9,
                abs_tol=1e-12,
            )
            or not isclose(
                float(movement.mass_delta_g),
                -float(mass_measurement.value),
                rel_tol=1e-12,
                abs_tol=1e-12,
            )
        ):
            raise WorkspaceInvariantError(
                "ACTION_INVENTORY_MOVEMENT_MISMATCH",
                f"Action commit {commit.id} changed quantity, stock, line, or reservation authority.",
            )

    for reservation_event in reservation_events:
        if (
            reservation_event.state == "FULFILLED"
            and reservation_event.id not in commit_by_fulfilled_event
        ):
            raise WorkspaceInvariantError(
                "FULFILLED_RESERVATION_COMMIT_MISSING",
                f"Fulfilled reservation event {reservation_event.id} lacks a canonical action commit.",
            )
    for movement in movements:
        if (
            movement.movement_type == "CONSUMPTION"
            and movement.build_plan_line_id is not None
            and movement.bottle_event_id is not None
            and movement.bottle_event_id not in commit_by_bottle_event
        ):
            raise WorkspaceInvariantError(
                "CONSUMPTION_ACTION_COMMIT_MISSING",
                f"Consumption movement {movement.id} is outside proposal-confirm-measure-commit authority.",
            )


async def _validate_plan_status_evidence(session: AsyncSession) -> None:
    plans = list(
        (
            await session.execute(
                select(LabBuildPlanVersion).order_by(
                    LabBuildPlanVersion.plan_id,
                    LabBuildPlanVersion.version_number,
                    LabBuildPlanVersion.id,
                )
            )
        ).scalars()
    )
    lines = list(
        (
            await session.execute(
                select(LabBuildPlanLine).order_by(
                    LabBuildPlanLine.build_plan_version_id,
                    LabBuildPlanLine.position,
                    LabBuildPlanLine.id,
                )
            )
        ).scalars()
    )
    reservation_events = list(
        (
            await session.execute(
                select(LabInventoryReservationEvent).order_by(
                    LabInventoryReservationEvent.reservation_id,
                    LabInventoryReservationEvent.sequence,
                    LabInventoryReservationEvent.id,
                )
            )
        ).scalars()
    )
    proposals = list((await session.execute(select(LabBottleActionProposal))).scalars())
    commits = list((await session.execute(select(LabBottleActionCommit))).scalars())

    plans_by_key: dict[str, list[LabBuildPlanVersion]] = defaultdict(list)
    lines_by_plan: dict[str, list[LabBuildPlanLine]] = defaultdict(list)
    reservation_chains: dict[str, list[LabInventoryReservationEvent]] = (
        defaultdict(list)
    )
    for plan in plans:
        plans_by_key[plan.plan_id].append(plan)
    for line in lines:
        lines_by_plan[line.build_plan_version_id].append(line)
    for event in reservation_events:
        reservation_chains[event.reservation_id].append(event)
    latest_event_by_reservation = {
        reservation_id: chain[-1]
        for reservation_id, chain in reservation_chains.items()
    }
    proposal_reservation_ids = {proposal.reservation_id for proposal in proposals}
    commit_fulfilled_event_ids = {
        commit.fulfilled_reservation_event_id for commit in commits
    }

    for versions in plans_by_key.values():
        latest = versions[-1]
        if latest.status not in {"RESERVED", "EXECUTING", "CLOSED"}:
            continue
        approved_versions = [
            version
            for version in versions
            if version.version_number <= latest.version_number
            and version.status == "APPROVED"
        ]
        if not approved_versions:
            raise WorkspaceInvariantError(
                "BUILD_PLAN_STATUS_EVIDENCE_MISSING",
                f"Build plan {latest.id} claims {latest.status} without an approved source version.",
            )
        approved = approved_versions[-1]
        approved_lines = lines_by_plan.get(approved.id, [])
        if not approved_lines:
            raise WorkspaceInvariantError(
                "BUILD_PLAN_STATUS_EVIDENCE_MISSING",
                f"Build plan {latest.id} claims {latest.status} without executable lines.",
            )
        latest_by_line: dict[str, LabInventoryReservationEvent] = {}
        for reservation_id, chain in reservation_chains.items():
            first = chain[0]
            if first.build_plan_version_id != approved.id:
                continue
            candidate_event = latest_event_by_reservation[reservation_id]
            prior = latest_by_line.get(first.build_plan_line_id)
            if prior is None or (
                candidate_event.created_at,
                candidate_event.id,
            ) > (
                prior.created_at,
                prior.id,
            ):
                latest_by_line[first.build_plan_line_id] = candidate_event
        selected_events: list[LabInventoryReservationEvent] = []
        for line in approved_lines:
            line_event = latest_by_line.get(line.id)
            if line_event is None or line_event.state not in {
                "RESERVED",
                "FULFILLED",
            }:
                raise WorkspaceInvariantError(
                    "BUILD_PLAN_STATUS_EVIDENCE_MISSING",
                    f"Build plan {latest.id} claims {latest.status} without reservation authority for every line.",
                )
            selected_events.append(line_event)
        if latest.status == "EXECUTING" and not any(
            event.reservation_id in proposal_reservation_ids
            for event in selected_events
        ):
            raise WorkspaceInvariantError(
                "BUILD_PLAN_STATUS_EVIDENCE_MISSING",
                f"Build plan {latest.id} claims EXECUTING without an action proposal.",
            )
        if latest.status == "CLOSED" and not all(
            event.state == "FULFILLED"
            and event.id in commit_fulfilled_event_ids
            for event in selected_events
        ):
            raise WorkspaceInvariantError(
                "BUILD_PLAN_STATUS_EVIDENCE_MISSING",
                f"Build plan {latest.id} claims CLOSED without terminal commits for every line.",
            )


async def _validate_bound_bottles(session: AsyncSession) -> None:
    result = await session.execute(
        select(LabBottleEvent, LabBottle)
        .join(LabBottle, LabBottleEvent.bottle_id == LabBottle.id)
        .where(LabBottle.batch_id.is_not(None))
        .order_by(LabBottleEvent.created_at, LabBottleEvent.id)
    )
    for event, bottle in result.all():
        if event.event_type == "TRANSFER":
            raise WorkspaceInvariantError(
                "BOUND_BOTTLE_FREEFORM_TRANSFER",
                f"Batch-bound bottle {bottle.id} contains a freeform transfer event.",
            )
        if event.event_type not in {"ADD_MATERIAL", "ADD_SOLVENT"}:
            continue
        movement_result = await session.execute(
            select(LabInventoryMovement).where(
                LabInventoryMovement.bottle_event_id == event.id
            )
        )
        movement = movement_result.scalar_one_or_none()
        if (
            movement is None
            or movement.build_plan_line_id is None
            or movement.reservation_event_id is None
        ):
            raise WorkspaceInvariantError(
                "BOUND_BOTTLE_FREEFORM_ADDITION",
                f"Batch-bound bottle {bottle.id} contains an addition outside proposal-confirm-measure-commit authority.",
            )


async def validate_workspace_invariants(
    session: AsyncSession,
    *,
    require_exact_stock_decimal: bool = False,
) -> None:
    """Replay all currently implemented stock/build/execution invariants."""

    await _validate_stock_solutions(
        session,
        require_exact_stock_decimal=require_exact_stock_decimal,
    )
    await _validate_inventory_ledger(session)
    try:
        await validate_workspace_stock_lineage(session)
    except StockLineageError as error:
        raise WorkspaceInvariantError(error.code, str(error)) from error
    await _validate_build_plans(session)
    await _validate_reservations_and_commits(session)
    await _validate_execution_chain(session)
    await _validate_plan_status_evidence(session)
    await _validate_bound_bottles(session)


__all__ = ["WorkspaceInvariantError", "validate_workspace_invariants"]
