"""Fail-closed projection from an immutable ideal to current exact stock.

This module is a proposal-layer boundary.  It preserves stock identity and
declared stock metadata, but it deliberately performs no dose, active amount,
ppm, OAV, or carrier-displacement calculation.  Any ambiguity or missing
quantitative authority produces ``HOLD`` rather than a guessed value.
"""

from __future__ import annotations

import json
import math
import re
import unicodedata
from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
from hashlib import sha256
from typing import Any, ClassVar, Iterable, Mapping, Sequence, cast

from .contracts import (
    AssessmentScope,
    AuthorityCeiling,
    ClaimCardinality,
    ClaimKind,
    EvidenceClass,
    PlaneAssessment,
    PlaneConflict,
    PlaneId,
    ProvenanceRef,
    ScopedClaim,
    UnknownFact,
)
from .target_compiler import (
    BuildProjectionId,
    TargetIntent,
    TargetResolution,
    create_build_projection_id,
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _text(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be text")
    normalized = " ".join(unicodedata.normalize("NFKC", value).split()).casefold()
    if not normalized:
        raise ValueError(f"{field_name} must be nonblank text")
    return normalized


def _optional_text(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    return _text(value, field_name)


def _text_tuple(
    values: Iterable[str],
    field_name: str,
    *,
    allow_empty: bool = True,
) -> tuple[str, ...]:
    normalized = tuple(_text(value, field_name) for value in values)
    if not allow_empty and not normalized:
        raise ValueError(f"{field_name} must not be empty")
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{field_name} must contain unique values")
    return tuple(sorted(normalized))


def _code_tuple(values: Iterable[str], field_name: str) -> tuple[str, ...]:
    normalized = tuple(_text(value, field_name).upper() for value in values)
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{field_name} must contain unique values")
    return tuple(sorted(normalized))


def _digest(value: object, field_name: str) -> str:
    normalized = _text(value, field_name)
    if not _SHA256_RE.fullmatch(normalized):
        raise ValueError(f"{field_name} must be a lowercase SHA-256 digest")
    return normalized


def _to_primitive(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        record_as_dict = getattr(value, "as_dict", None)
        if callable(record_as_dict):
            return _to_primitive(record_as_dict())
        return {item.name: _to_primitive(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, Mapping):
        return {
            str(key): _to_primitive(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (tuple, list)):
        return [_to_primitive(item) for item in value]
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("canonical JSON does not permit non-finite floats")
        return value
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise TypeError(f"{type(value).__name__} is not canonically serializable")


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        _to_primitive(value),
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _payload(payload: Mapping[str, Any], record_type: type[Any]) -> Mapping[str, Any]:
    """Require one exact, closed dataclass schema for every persisted record."""

    if not isinstance(payload, Mapping):
        raise TypeError("payload must be a mapping")
    schema_version = record_type.SCHEMA_VERSION
    declared = payload.get("schema_version")
    if declared != schema_version:
        raise ValueError(f"schema_version must be {schema_version!r}, received {declared!r}")
    expected = {"schema_version", *(item.name for item in fields(record_type))}
    supplied = set(payload)
    missing = sorted(expected - supplied)
    extra = sorted(supplied - expected)
    if missing or extra:
        details: list[str] = []
        if missing:
            details.append("missing fields: " + ", ".join(missing))
        if extra:
            details.append("unexpected fields: " + ", ".join(extra))
        raise ValueError(f"{record_type.__name__} payload is not closed: " + "; ".join(details))
    return payload


def _sequence(value: object, field_name: str) -> Sequence[Any]:
    if not isinstance(value, (list, tuple)):
        raise TypeError(f"{field_name} must be a sequence")
    return value


def _mapping(value: object, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a mapping")
    return value


def _bool(value: object, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{field_name} must be bool")
    return value


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", _text(value, "identifier")).strip("-")


class _CanonicalProjectionRecord:
    SCHEMA_VERSION: ClassVar[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            **{
                item.name: _to_primitive(getattr(self, item.name))
                for item in fields(cast(Any, self))
            },
        }

    @property
    def content_sha256(self) -> str:
        return sha256(_canonical_json_bytes(self.as_dict())).hexdigest()


class StockAvailability(str, Enum):
    """Physical-current state; historical or tombstoned is never current stock."""

    OWNED = "owned"
    UNAVAILABLE = "unavailable"
    DEPLETED = "depleted"
    HISTORICAL_ONLY = "historical_only"
    TOMBSTONED = "tombstoned"


class AliquotState(str, Enum):
    """Whether the exact stock can supply a homogeneous, bound aliquot."""

    READY = "ready"
    UNKNOWN = "unknown"
    NOT_PREPARED = "not_prepared"
    HETEROGENEOUS = "heterogeneous"


class ProjectionDisposition(str, Enum):
    """Proposal state; none of these values authorizes physical execution."""

    BUILD_IDENTIFIED = "build_identified"
    HOLD = "hold"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class IdealMaterialSelection(_CanonicalProjectionRecord):
    """One target-linked ideal selection with no inventory or dose surface."""

    SCHEMA_VERSION = "ideal_material_selection_v1"

    selection_id: str
    material_name: str
    target_function: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "selection_id", _text(self.selection_id, "selection_id"))
        object.__setattr__(self, "material_name", _text(self.material_name, "material_name"))
        object.__setattr__(
            self,
            "target_function",
            _text(self.target_function, "target_function"),
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> IdealMaterialSelection:
        data = _payload(payload, cls)
        return cls(
            selection_id=data["selection_id"],
            material_name=data["material_name"],
            target_function=data["target_function"],
        )


@dataclass(frozen=True, slots=True)
class IdealProposal(_CanonicalProjectionRecord):
    """Immutable TARGET/IDEAL proposal, deliberately independent of inventory."""

    SCHEMA_VERSION = "ideal_inventory_independent_proposal_v2"

    proposal_id: str
    target_intent: TargetIntent
    selections: tuple[IdealMaterialSelection, ...]
    design_notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "proposal_id", _text(self.proposal_id, "proposal_id"))
        if not isinstance(self.target_intent, TargetIntent):
            raise TypeError("target_intent must be a TargetIntent")
        by_id: dict[str, IdealMaterialSelection] = {}
        for selection in self.selections:
            if not isinstance(selection, IdealMaterialSelection):
                raise TypeError("selections must contain IdealMaterialSelection values")
            if selection.selection_id in by_id:
                raise ValueError("selections must contain unique selection_id values")
            by_id[selection.selection_id] = selection
        if not by_id:
            raise ValueError("selections must not be empty")
        object.__setattr__(
            self,
            "selections",
            tuple(by_id[key] for key in sorted(by_id)),
        )
        object.__setattr__(
            self,
            "design_notes",
            _text_tuple(self.design_notes, "design_notes"),
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> IdealProposal:
        data = _payload(payload, cls)
        return cls(
            proposal_id=data["proposal_id"],
            target_intent=TargetIntent.from_dict(
                _mapping(data["target_intent"], "target_intent")
            ),
            selections=tuple(
                IdealMaterialSelection.from_dict(
                    _mapping(item, "selections item")
                )
                for item in _sequence(data["selections"], "selections")
            ),
            design_notes=tuple(_sequence(data["design_notes"], "design_notes")),
        )

    @property
    def ideal_target_id(self) -> str:
        """Typed semantic target identity; inventory cannot rewrite it."""

        return self.target_intent.ideal_target_id.value


@dataclass(frozen=True, slots=True)
class ExactStockRef(_CanonicalProjectionRecord):
    """One exact physical, historical, or tombstoned stock declaration."""

    SCHEMA_VERSION = "formulation_exact_stock_ref_v1"

    exact_stock_ref: str
    material_name: str
    availability: StockAvailability
    fraction: float | None
    fraction_basis: str | None
    carrier: str | None
    aliquot_state: AliquotState
    authority_source: str
    exact_identity: bool = False
    quantitative_authority: bool = False
    composition_complete: bool = False
    authority_notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "exact_stock_ref",
            _text(self.exact_stock_ref, "exact_stock_ref"),
        )
        object.__setattr__(self, "material_name", _text(self.material_name, "material_name"))
        object.__setattr__(self, "availability", StockAvailability(self.availability))
        object.__setattr__(self, "aliquot_state", AliquotState(self.aliquot_state))
        if self.fraction is not None:
            if isinstance(self.fraction, bool) or not isinstance(self.fraction, (int, float)):
                raise TypeError("fraction must be a finite number or None")
            fraction = float(self.fraction)
            if not math.isfinite(fraction) or not 0.0 < fraction <= 1.0:
                raise ValueError("fraction must be within (0, 1]")
            object.__setattr__(self, "fraction", fraction)
        object.__setattr__(
            self,
            "fraction_basis",
            _optional_text(self.fraction_basis, "fraction_basis"),
        )
        object.__setattr__(self, "carrier", _optional_text(self.carrier, "carrier"))
        object.__setattr__(
            self,
            "authority_source",
            _text(self.authority_source, "authority_source"),
        )
        for field_name in (
            "exact_identity",
            "quantitative_authority",
            "composition_complete",
        ):
            if not isinstance(getattr(self, field_name), bool):
                raise TypeError(f"{field_name} must be bool")
        object.__setattr__(
            self,
            "authority_notes",
            _text_tuple(self.authority_notes, "authority_notes"),
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ExactStockRef:
        data = _payload(payload, cls)
        return cls(
            exact_stock_ref=data["exact_stock_ref"],
            material_name=data["material_name"],
            availability=StockAvailability(data["availability"]),
            fraction=data["fraction"],
            fraction_basis=data["fraction_basis"],
            carrier=data["carrier"],
            aliquot_state=AliquotState(data["aliquot_state"]),
            authority_source=data["authority_source"],
            exact_identity=_bool(data["exact_identity"], "exact_identity"),
            quantitative_authority=_bool(
                data["quantitative_authority"], "quantitative_authority"
            ),
            composition_complete=_bool(
                data["composition_complete"], "composition_complete"
            ),
            authority_notes=tuple(
                _sequence(data["authority_notes"], "authority_notes")
            ),
        )


@dataclass(frozen=True, slots=True)
class InventoryProjectionLine(_CanonicalProjectionRecord):
    """One ideal-to-stock mapping; quantitative outputs are intentionally absent."""

    SCHEMA_VERSION = "inventory_projection_line_v1"

    selection_id: str
    ideal_material_name: str
    target_function: str
    disposition: ProjectionDisposition
    exact_stock_ref: str | None
    candidate_stock_refs: tuple[str, ...]
    fraction: float | None
    fraction_basis: str | None
    carrier: str | None
    aliquot_state: AliquotState | None
    hold_reasons: tuple[str, ...]
    active_amount_ul: float | None = None
    concentration_ppm: float | None = None
    oav: float | None = None
    carrier_displacement_ul: float | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "selection_id", _text(self.selection_id, "selection_id"))
        object.__setattr__(
            self,
            "ideal_material_name",
            _text(self.ideal_material_name, "ideal_material_name"),
        )
        object.__setattr__(
            self,
            "target_function",
            _text(self.target_function, "target_function"),
        )
        disposition = ProjectionDisposition(self.disposition)
        object.__setattr__(self, "disposition", disposition)
        object.__setattr__(
            self,
            "exact_stock_ref",
            _optional_text(self.exact_stock_ref, "exact_stock_ref"),
        )
        candidates = _text_tuple(self.candidate_stock_refs, "candidate_stock_refs")
        object.__setattr__(self, "candidate_stock_refs", candidates)
        if self.fraction is not None:
            if isinstance(self.fraction, bool) or not isinstance(self.fraction, (int, float)):
                raise TypeError("fraction must be a finite number or None")
            fraction = float(self.fraction)
            if not math.isfinite(fraction) or not 0.0 < fraction <= 1.0:
                raise ValueError("fraction must be within (0, 1]")
            object.__setattr__(self, "fraction", fraction)
        object.__setattr__(
            self,
            "fraction_basis",
            _optional_text(self.fraction_basis, "fraction_basis"),
        )
        object.__setattr__(self, "carrier", _optional_text(self.carrier, "carrier"))
        if self.aliquot_state is not None:
            object.__setattr__(self, "aliquot_state", AliquotState(self.aliquot_state))
        reasons = _code_tuple(self.hold_reasons, "hold_reasons")
        object.__setattr__(self, "hold_reasons", reasons)

        quantitative_fields = (
            "active_amount_ul",
            "concentration_ppm",
            "oav",
            "carrier_displacement_ul",
        )
        if any(getattr(self, field_name) is not None for field_name in quantitative_fields):
            raise ValueError(
                "inventory projection is proposal-only and cannot contain calculated "
                "active amount, ppm, OAV, or carrier displacement"
            )
        if disposition is ProjectionDisposition.BUILD_IDENTIFIED:
            if self.exact_stock_ref is None or reasons:
                raise ValueError("BUILD_IDENTIFIED requires one exact stock and no holds")
        elif not reasons:
            raise ValueError("HOLD/UNAVAILABLE projection lines require hold_reasons")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> InventoryProjectionLine:
        data = _payload(payload, cls)
        return cls(
            selection_id=data["selection_id"],
            ideal_material_name=data["ideal_material_name"],
            target_function=data["target_function"],
            disposition=ProjectionDisposition(data["disposition"]),
            exact_stock_ref=data["exact_stock_ref"],
            candidate_stock_refs=tuple(
                _sequence(data["candidate_stock_refs"], "candidate_stock_refs")
            ),
            fraction=data["fraction"],
            fraction_basis=data["fraction_basis"],
            carrier=data["carrier"],
            aliquot_state=(
                AliquotState(data["aliquot_state"])
                if data["aliquot_state"] is not None
                else None
            ),
            hold_reasons=tuple(_sequence(data["hold_reasons"], "hold_reasons")),
            active_amount_ul=data["active_amount_ul"],
            concentration_ppm=data["concentration_ppm"],
            oav=data["oav"],
            carrier_displacement_ul=data["carrier_displacement_ul"],
        )


@dataclass(frozen=True, slots=True)
class InventoryProjection(_CanonicalProjectionRecord):
    """Content-addressed CURRENT-INVENTORY BUILD proposal."""

    SCHEMA_VERSION = "current_inventory_build_projection_v2"

    projection_id: str
    ideal_proposal: IdealProposal
    build_projection_id: BuildProjectionId
    inventory_content_sha256: str
    stock_authority_overlay_sha256: str
    stock_authority_records_sha256: str
    stock_authority_snapshot_id: str
    stock_authority_records: tuple[ExactStockRef, ...]
    disposition: ProjectionDisposition
    lines: tuple[InventoryProjectionLine, ...]
    authority_ceiling: AuthorityCeiling
    physical_execution_authorized: bool = False
    release_authorized: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.ideal_proposal, IdealProposal):
            raise TypeError("ideal_proposal must be an IdealProposal")
        if not isinstance(self.build_projection_id, BuildProjectionId):
            raise TypeError("build_projection_id must be a BuildProjectionId")
        object.__setattr__(
            self,
            "inventory_content_sha256",
            _digest(self.inventory_content_sha256, "inventory_content_sha256"),
        )
        object.__setattr__(
            self,
            "stock_authority_overlay_sha256",
            _digest(
                self.stock_authority_overlay_sha256,
                "stock_authority_overlay_sha256",
            ),
        )
        object.__setattr__(
            self,
            "stock_authority_snapshot_id",
            _text(self.stock_authority_snapshot_id, "stock_authority_snapshot_id"),
        )
        if self.build_projection_id.ideal_target_id != self.target_intent.ideal_target_id:
            raise ValueError("build projection target does not match typed target intent")
        if (
            self.build_projection_id.inventory_content_sha256
            != self.inventory_content_sha256
        ):
            raise ValueError("build projection inventory hash does not match inventory content")
        if (
            self.build_projection_id.stock_authority_snapshot_id
            != self.stock_authority_snapshot_id
        ):
            raise ValueError("build projection stock authority snapshot does not match")

        by_ref: dict[str, ExactStockRef] = {}
        for stock in self.stock_authority_records:
            if not isinstance(stock, ExactStockRef):
                raise TypeError("stock_authority_records must contain ExactStockRef values")
            current = by_ref.get(stock.exact_stock_ref)
            if current is not None and current != stock:
                raise ValueError(
                    f"conflicting exact stock definition: {stock.exact_stock_ref!r}"
                )
            if current is not None:
                raise ValueError("stock_authority_records must contain unique exact_stock_ref")
            by_ref[stock.exact_stock_ref] = stock
        records = tuple(by_ref[key] for key in sorted(by_ref))
        object.__setattr__(self, "stock_authority_records", records)
        expected_records_sha256 = _stock_authority_records_sha256(records)
        supplied_records_sha256 = _digest(
            self.stock_authority_records_sha256,
            "stock_authority_records_sha256",
        )
        if supplied_records_sha256 != expected_records_sha256:
            raise ValueError(
                "stock_authority_records_sha256 does not bind the complete stock records"
            )
        object.__setattr__(
            self,
            "stock_authority_records_sha256",
            supplied_records_sha256,
        )

        disposition = ProjectionDisposition(self.disposition)
        object.__setattr__(self, "disposition", disposition)
        by_id: dict[str, InventoryProjectionLine] = {}
        for line in self.lines:
            if not isinstance(line, InventoryProjectionLine):
                raise TypeError("lines must contain InventoryProjectionLine values")
            if line.selection_id in by_id:
                raise ValueError("lines must contain unique selection_id values")
            by_id[line.selection_id] = line
        if not by_id:
            raise ValueError("lines must not be empty")
        lines = tuple(by_id[key] for key in sorted(by_id))
        object.__setattr__(self, "lines", lines)
        selection_by_id = {
            selection.selection_id: selection
            for selection in self.ideal_proposal.selections
        }
        if set(by_id) != set(selection_by_id):
            raise ValueError("projection lines must cover every ideal selection exactly once")
        record_ids = set(by_ref)
        for line in lines:
            selection = selection_by_id[line.selection_id]
            if (
                line.ideal_material_name != selection.material_name
                or line.target_function != selection.target_function
            ):
                raise ValueError("projection line rewrites its ideal selection")
            cited = set(line.candidate_stock_refs)
            if line.exact_stock_ref is not None:
                cited.add(line.exact_stock_ref)
            dangling = sorted(cited - record_ids)
            if dangling:
                raise ValueError(
                    "projection line cites omitted stock authority records: "
                    + ", ".join(dangling)
                )
        expected_disposition = (
            ProjectionDisposition.BUILD_IDENTIFIED
            if all(line.disposition is ProjectionDisposition.BUILD_IDENTIFIED for line in lines)
            else ProjectionDisposition.HOLD
        )
        if disposition is not expected_disposition:
            raise ValueError("projection disposition does not match line dispositions")
        expected_authority = (
            AuthorityCeiling.STRUCTURAL_ONLY
            if disposition is ProjectionDisposition.BUILD_IDENTIFIED
            and self.target_intent.resolution is TargetResolution.RESOLVED_FOR_DESIGN
            else AuthorityCeiling.WITHHELD
        )
        authority = AuthorityCeiling(self.authority_ceiling)
        if authority is not expected_authority:
            raise ValueError("inventory projection authority does not match held source state")
        object.__setattr__(self, "authority_ceiling", authority)
        for field_name in ("physical_execution_authorized", "release_authorized"):
            value = getattr(self, field_name)
            if not isinstance(value, bool):
                raise TypeError(f"{field_name} must be bool")
            if value is not False:
                raise ValueError(f"{field_name} cannot be promoted by inventory projection")
        expected_id = _projection_id(
            ideal_proposal_sha256=self.ideal_proposal.content_sha256,
            target_intent_sha256=self.target_intent.content_sha256,
            build_projection_sha256=self.build_projection_id.content_sha256,
            inventory_content_sha256=self.inventory_content_sha256,
            stock_authority_overlay_sha256=self.stock_authority_overlay_sha256,
            stock_authority_records_sha256=self.stock_authority_records_sha256,
            stock_authority_snapshot_id=self.stock_authority_snapshot_id,
            lines=lines,
            authority_ceiling=authority,
        )
        supplied = _text(self.projection_id, "projection_id")
        if supplied != expected_id:
            raise ValueError("projection_id does not match projection content")
        object.__setattr__(self, "projection_id", supplied)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> InventoryProjection:
        data = _payload(payload, cls)
        return cls(
            projection_id=data["projection_id"],
            ideal_proposal=IdealProposal.from_dict(
                _mapping(data["ideal_proposal"], "ideal_proposal")
            ),
            build_projection_id=BuildProjectionId.from_dict(
                _mapping(data["build_projection_id"], "build_projection_id")
            ),
            inventory_content_sha256=data["inventory_content_sha256"],
            stock_authority_overlay_sha256=data["stock_authority_overlay_sha256"],
            stock_authority_records_sha256=data["stock_authority_records_sha256"],
            stock_authority_snapshot_id=data["stock_authority_snapshot_id"],
            stock_authority_records=tuple(
                ExactStockRef.from_dict(
                    _mapping(item, "stock_authority_records item")
                )
                for item in _sequence(
                    data["stock_authority_records"], "stock_authority_records"
                )
            ),
            disposition=ProjectionDisposition(data["disposition"]),
            lines=tuple(
                InventoryProjectionLine.from_dict(_mapping(item, "lines item"))
                for item in _sequence(data["lines"], "lines")
            ),
            authority_ceiling=AuthorityCeiling(data["authority_ceiling"]),
            physical_execution_authorized=_bool(
                data["physical_execution_authorized"],
                "physical_execution_authorized",
            ),
            release_authorized=_bool(
                data["release_authorized"], "release_authorized"
            ),
        )

    @property
    def target_intent(self) -> TargetIntent:
        return self.ideal_proposal.target_intent

    @property
    def ideal_proposal_sha256(self) -> str:
        return self.ideal_proposal.content_sha256

    @property
    def target_intent_sha256(self) -> str:
        return self.target_intent.content_sha256

    @property
    def ideal_target_id(self) -> str:
        return self.ideal_proposal.ideal_target_id

    def to_plane_assessment(self) -> PlaneAssessment:
        """Emit an exact-scope INVENTORY_BUILD structural receipt.

        This adapter carries mapping dispositions and every authority hold.  It
        intentionally emits no support interval, active amount, ppm, OAV,
        carrier displacement, sensory observation, or execution permission.
        """

        target_assessment = self.target_intent.to_plane_assessment()
        stock_by_ref = {
            stock.exact_stock_ref: stock for stock in self.stock_authority_records
        }
        stock_provenance = {
            stock.exact_stock_ref: ProvenanceRef(
                provenance_id=f"inventory-stock-{stock.content_sha256[:24]}",
                source_ref=stock.authority_source,
                evidence_class=EvidenceClass.UNKNOWN,
                independence_key=f"inventory-stock-{_slug(stock.exact_stock_ref)}",
                source_sha256=stock.content_sha256,
            )
            for stock in self.stock_authority_records
        }
        claims: list[ScopedClaim] = []
        unknowns: list[UnknownFact] = []
        conflicts: list[PlaneConflict] = []
        experiments: list[str] = []

        for line in self.lines:
            referenced = tuple(
                stock_provenance[reference]
                for reference in line.candidate_stock_refs
                if reference in stock_provenance
            )
            exact = (
                stock_by_ref[line.exact_stock_ref]
                if line.exact_stock_ref is not None
                else None
            )
            exact_hash = exact.content_sha256 if exact is not None else "none"
            claim = ScopedClaim(
                claim_id=f"inventory-line-{_slug(line.selection_id)}",
                claim_key="inventory_projection_line",
                claim_value=(
                    f"selection={line.selection_id}; ideal={line.ideal_material_name}; "
                    f"function={line.target_function}; disposition={line.disposition.value}; "
                    f"exact_stock_ref={line.exact_stock_ref or 'none'}; "
                    f"authority_record_sha256={exact_hash}; "
                    f"fraction={line.fraction if line.fraction is not None else 'unknown'}; "
                    f"fraction_basis={line.fraction_basis or 'unknown'}; "
                    f"carrier={line.carrier or 'unknown'}; "
                    f"aliquot_state={line.aliquot_state.value if line.aliquot_state else 'unknown'}"
                ),
                claim_kind=ClaimKind.DIAGNOSTIC,
                authority_ceiling=self.authority_ceiling,
                provenance_refs=tuple(
                    sorted(
                        {*target_assessment.provenance_refs, *referenced},
                        key=lambda item: item.content_sha256,
                    )
                ),
                cardinality=ClaimCardinality.SET_MEMBER,
                member_id=f"selection-{_slug(line.selection_id)}",
            )
            claims.append(claim)
            for reason in line.hold_reasons:
                unknowns.append(
                    UnknownFact(
                        unknown_id=(
                            f"inventory-{_slug(line.selection_id)}-{_slug(reason)}"
                        ),
                        field_key=(
                            f"inventory-{_slug(line.selection_id)}-{_slug(reason)}"
                        ),
                        reason=f"inventory authority hold: {reason}",
                        needed_evidence=(
                            f"exact authority record resolving {reason} for "
                            f"{line.ideal_material_name}"
                        ),
                        provenance_refs=referenced,
                    )
                )
                experiments.append(
                    f"resolve inventory authority {reason} for selection {line.selection_id}"
                )
            if len(line.candidate_stock_refs) > 1:
                conflicts.append(
                    PlaneConflict(
                        conflict_id=f"inventory-stock-choice-{_slug(line.selection_id)}",
                        claim_key="inventory_projection_line",
                        alternatives=line.candidate_stock_refs,
                        reason="multiple stock authority records match one ideal selection",
                        claim_ids=(claim.claim_id,),
                        provenance_refs=referenced,
                    )
                )

        all_stock_provenance = tuple(
            sorted(stock_provenance.values(), key=lambda item: item.content_sha256)
        )
        return PlaneAssessment(
            assessment_id=f"inventory-build/{self.projection_id.rsplit('/', 1)[-1]}",
            module_id="inventory-projection-v2",
            plane_id=PlaneId.INVENTORY_BUILD,
            scope=AssessmentScope(
                target_scope=target_assessment.scope.target_scope,
                temporal_scope=target_assessment.scope.temporal_scope,
                matrix_scope=target_assessment.scope.matrix_scope,
            ),
            claims=tuple(claims),
            support_intervals=(),
            conflicts=tuple(conflicts),
            unknowns=tuple(unknowns),
            failure_modes=(
                "inventory rewrites the ideal target",
                "stock identity ambiguity is guessed",
                "unresolved stock metadata is converted into quantitative math",
                "inventory projection is treated as physical execution authority",
            ),
            proposed_experiments=tuple(experiments),
            provenance_refs=tuple(
                sorted(
                    {*target_assessment.provenance_refs, *all_stock_provenance},
                    key=lambda item: item.content_sha256,
                )
            ),
            authority_ceiling=self.authority_ceiling,
            freshness_hashes=(
                self.target_intent.content_sha256,
                self.ideal_proposal.content_sha256,
                self.build_projection_id.content_sha256,
                self.inventory_content_sha256,
                self.stock_authority_overlay_sha256,
                self.stock_authority_records_sha256,
            ),
            native_criteria=(),
        )


def _projection_id(
    *,
    ideal_proposal_sha256: str,
    target_intent_sha256: str,
    build_projection_sha256: str,
    inventory_content_sha256: str,
    stock_authority_overlay_sha256: str,
    stock_authority_records_sha256: str,
    stock_authority_snapshot_id: str,
    lines: tuple[InventoryProjectionLine, ...],
    authority_ceiling: AuthorityCeiling,
) -> str:
    digest = sha256(
        _canonical_json_bytes(
            {
                "schema_version": "inventory_projection_identity_payload_v2",
                "ideal_proposal_sha256": ideal_proposal_sha256,
                "target_intent_sha256": target_intent_sha256,
                "build_projection_sha256": build_projection_sha256,
                "inventory_content_sha256": inventory_content_sha256,
                "stock_authority_overlay_sha256": stock_authority_overlay_sha256,
                "stock_authority_records_sha256": stock_authority_records_sha256,
                "stock_authority_snapshot_id": stock_authority_snapshot_id,
                "lines": lines,
                "authority_ceiling": authority_ceiling,
            }
        )
    ).hexdigest()
    return f"inventory-projection/{digest}"


def _stock_authority_records_sha256(records: tuple[ExactStockRef, ...]) -> str:
    """Hash every stock-authority field, including source prose and notes."""

    return sha256(
        _canonical_json_bytes(
            {
                "schema_version": "stock_authority_records_payload_v1",
                "records": records,
            }
        )
    ).hexdigest()


_UNRESOLVED_MARKERS = frozenset({"unspecified", "unknown", "unresolved"})


def _stock_hold_reasons(stock: ExactStockRef) -> tuple[str, ...]:
    reasons: list[str] = []
    if stock.availability is not StockAvailability.OWNED:
        reasons.append(f"AVAILABILITY_{stock.availability.value.upper()}")
    if not stock.exact_identity:
        reasons.append("EXACT_IDENTITY_UNRESOLVED")
    if stock.fraction is None:
        reasons.append("FRACTION_UNRESOLVED")
    if stock.fraction_basis is None or stock.fraction_basis in _UNRESOLVED_MARKERS:
        reasons.append("FRACTION_BASIS_UNRESOLVED")
    if stock.carrier is None or stock.carrier in _UNRESOLVED_MARKERS:
        reasons.append("CARRIER_UNRESOLVED")
    if stock.aliquot_state is not AliquotState.READY:
        reasons.append("ALIQUOT_NOT_READY")
    if not stock.quantitative_authority:
        reasons.append("QUANTITATIVE_AUTHORITY_WITHHELD")
    if not stock.composition_complete:
        reasons.append("COMPOSITION_INCOMPLETE")
    return tuple(sorted(set(reasons)))


def _line_for_selection(
    selection: IdealMaterialSelection,
    stock_refs: tuple[ExactStockRef, ...],
) -> InventoryProjectionLine:
    matches = tuple(
        sorted(
            (item for item in stock_refs if item.material_name == selection.material_name),
            key=lambda item: item.exact_stock_ref,
        )
    )
    current = tuple(item for item in matches if item.availability is StockAvailability.OWNED)
    if len(current) > 1:
        return InventoryProjectionLine(
            selection_id=selection.selection_id,
            ideal_material_name=selection.material_name,
            target_function=selection.target_function,
            disposition=ProjectionDisposition.HOLD,
            exact_stock_ref=None,
            candidate_stock_refs=tuple(item.exact_stock_ref for item in current),
            fraction=None,
            fraction_basis=None,
            carrier=None,
            aliquot_state=None,
            hold_reasons=("AMBIGUOUS_EXACT_STOCK_REF",),
        )
    if len(current) == 1:
        stock = current[0]
        reasons = _stock_hold_reasons(stock)
        return InventoryProjectionLine(
            selection_id=selection.selection_id,
            ideal_material_name=selection.material_name,
            target_function=selection.target_function,
            disposition=(
                ProjectionDisposition.HOLD if reasons else ProjectionDisposition.BUILD_IDENTIFIED
            ),
            exact_stock_ref=stock.exact_stock_ref,
            candidate_stock_refs=(stock.exact_stock_ref,),
            fraction=stock.fraction,
            fraction_basis=stock.fraction_basis,
            carrier=stock.carrier,
            aliquot_state=stock.aliquot_state,
            hold_reasons=reasons,
        )
    if len(matches) == 1:
        stock = matches[0]
        reasons = _stock_hold_reasons(stock)
        return InventoryProjectionLine(
            selection_id=selection.selection_id,
            ideal_material_name=selection.material_name,
            target_function=selection.target_function,
            disposition=ProjectionDisposition.UNAVAILABLE,
            exact_stock_ref=stock.exact_stock_ref,
            candidate_stock_refs=(stock.exact_stock_ref,),
            fraction=stock.fraction,
            fraction_basis=stock.fraction_basis,
            carrier=stock.carrier,
            aliquot_state=stock.aliquot_state,
            hold_reasons=reasons or ("NO_CURRENT_OWNED_STOCK",),
        )
    if len(matches) > 1:
        return InventoryProjectionLine(
            selection_id=selection.selection_id,
            ideal_material_name=selection.material_name,
            target_function=selection.target_function,
            disposition=ProjectionDisposition.HOLD,
            exact_stock_ref=None,
            candidate_stock_refs=tuple(item.exact_stock_ref for item in matches),
            fraction=None,
            fraction_basis=None,
            carrier=None,
            aliquot_state=None,
            hold_reasons=("AMBIGUOUS_NONCURRENT_STOCK_HISTORY",),
        )
    return InventoryProjectionLine(
        selection_id=selection.selection_id,
        ideal_material_name=selection.material_name,
        target_function=selection.target_function,
        disposition=ProjectionDisposition.HOLD,
        exact_stock_ref=None,
        candidate_stock_refs=(),
        fraction=None,
        fraction_basis=None,
        carrier=None,
        aliquot_state=None,
        hold_reasons=("NO_EXACT_STOCK_REF",),
    )


def project_ideal_to_current_build(
    ideal: IdealProposal,
    exact_stock_refs: Iterable[ExactStockRef],
    *,
    inventory_content_sha256: str,
    stock_authority_overlay_sha256: str,
    stock_authority_snapshot_id: str,
    projection_variant: str = "exact-stock-proposal-v1",
) -> InventoryProjection:
    """Project an ideal by exact identity; never mutate it or infer quantities."""

    if not isinstance(ideal, IdealProposal):
        raise TypeError("ideal must be an IdealProposal")
    inventory_hash = _digest(inventory_content_sha256, "inventory_content_sha256")
    overlay_hash = _digest(
        stock_authority_overlay_sha256,
        "stock_authority_overlay_sha256",
    )
    authority_id = _text(stock_authority_snapshot_id, "stock_authority_snapshot_id")
    by_ref: dict[str, ExactStockRef] = {}
    for stock in exact_stock_refs:
        if not isinstance(stock, ExactStockRef):
            raise TypeError("exact_stock_refs must contain ExactStockRef values")
        current = by_ref.get(stock.exact_stock_ref)
        if current is not None and current != stock:
            raise ValueError(f"conflicting exact stock definition: {stock.exact_stock_ref!r}")
        by_ref[stock.exact_stock_ref] = stock
    stocks = tuple(by_ref[key] for key in sorted(by_ref))
    lines = tuple(_line_for_selection(selection, stocks) for selection in ideal.selections)
    disposition = (
        ProjectionDisposition.BUILD_IDENTIFIED
        if all(line.disposition is ProjectionDisposition.BUILD_IDENTIFIED for line in lines)
        else ProjectionDisposition.HOLD
    )
    authority_ceiling = (
        AuthorityCeiling.STRUCTURAL_ONLY
        if disposition is ProjectionDisposition.BUILD_IDENTIFIED
        and ideal.target_intent.resolution is TargetResolution.RESOLVED_FOR_DESIGN
        else AuthorityCeiling.WITHHELD
    )
    records_sha256 = _stock_authority_records_sha256(stocks)
    build_projection_id = create_build_projection_id(
        ideal.target_intent,
        inventory_content_sha256=inventory_hash,
        stock_authority_snapshot_id=authority_id,
        projection_variant=projection_variant,
    )
    projection_id = _projection_id(
        ideal_proposal_sha256=ideal.content_sha256,
        target_intent_sha256=ideal.target_intent.content_sha256,
        build_projection_sha256=build_projection_id.content_sha256,
        inventory_content_sha256=inventory_hash,
        stock_authority_overlay_sha256=overlay_hash,
        stock_authority_records_sha256=records_sha256,
        stock_authority_snapshot_id=authority_id,
        lines=lines,
        authority_ceiling=authority_ceiling,
    )
    return InventoryProjection(
        projection_id=projection_id,
        ideal_proposal=ideal,
        build_projection_id=build_projection_id,
        inventory_content_sha256=inventory_hash,
        stock_authority_overlay_sha256=overlay_hash,
        stock_authority_records_sha256=records_sha256,
        stock_authority_snapshot_id=authority_id,
        stock_authority_records=stocks,
        disposition=disposition,
        lines=lines,
        authority_ceiling=authority_ceiling,
    )


def current_inventory_stock_corrections() -> tuple[ExactStockRef, ...]:
    """Return the frozen 2026-08-30 authority corrections required by WP-10.

    These records describe selection/executability authority only.  They grant no
    sensory, safety, stability, physical-compounding, purchase, or release claim.
    """

    records = (
        ExactStockRef(
            exact_stock_ref="inventory:v7:magnolia-eo:as-supplied",
            material_name="Magnolia EO",
            availability=StockAvailability.OWNED,
            fraction=1.0,
            fraction_basis="neat_as_supplied",
            carrier="none",
            aliquot_state=AliquotState.READY,
            authority_source="inventory.txt user correction 2026-08-30",
            exact_identity=True,
            quantitative_authority=True,
            composition_complete=True,
            authority_notes=("neat/as supplied; lot and botanical detail unresolved",),
        ),
        ExactStockRef(
            exact_stock_ref="inventory:v7:alpha-irone:10pct-ww-dep",
            material_name="Alpha Irone",
            availability=StockAvailability.OWNED,
            fraction=0.10,
            fraction_basis="w/w",
            carrier="DEP",
            aliquot_state=AliquotState.READY,
            authority_source="inventory user authority overlay 2026-08-28",
            exact_identity=True,
            quantitative_authority=True,
            composition_complete=True,
            authority_notes=("only current Alpha Irone stock",),
        ),
        ExactStockRef(
            exact_stock_ref="inventory:v7:black-agarwood-artificial:10pct-ww-dpg",
            material_name="Black Agarwood Artificial",
            availability=StockAvailability.OWNED,
            fraction=0.10,
            fraction_basis="w/w",
            carrier="DPG",
            aliquot_state=AliquotState.READY,
            authority_source="inventory user correction 2026-08-30",
            exact_identity=True,
            quantitative_authority=True,
            composition_complete=True,
            authority_notes=("only current stock; no neat bottle is owned",),
        ),
        ExactStockRef(
            exact_stock_ref="inventory:v8:cabreuva-eo:50pct-ww-dpg",
            material_name="Cabreuva EO",
            availability=StockAvailability.OWNED,
            fraction=0.50,
            fraction_basis="w/w",
            carrier="DPG",
            aliquot_state=AliquotState.READY,
            authority_source="inventory.txt current stock declaration 2026-09-01",
            exact_identity=True,
            quantitative_authority=True,
            composition_complete=True,
            authority_notes=(
                "one-half Cabreuva EO by mass in DPG",
                "natural constituent composition and lot remain unasserted",
            ),
        ),
        ExactStockRef(
            exact_stock_ref="inventory:v8:cypress-eo:neat-as-supplied",
            material_name="Cypress EO",
            availability=StockAvailability.OWNED,
            fraction=1.0,
            fraction_basis="neat_as_supplied",
            carrier="none",
            aliquot_state=AliquotState.READY,
            authority_source="user neat-stock correction 2026-08-30",
            exact_identity=True,
            quantitative_authority=True,
            composition_complete=True,
            authority_notes=(
                "Aroma&More via Shopee user-authoritative stock",
                "species, chemotype, lot, COA, and density remain unasserted",
                "user quality report is not hedonic or release evidence",
            ),
        ),
        ExactStockRef(
            exact_stock_ref="inventory:tombstone:black-agarwood-artificial:neat",
            material_name="Black Agarwood Artificial",
            availability=StockAvailability.TOMBSTONED,
            fraction=1.0,
            fraction_basis="neat_as_supplied",
            carrier="none",
            aliquot_state=AliquotState.NOT_PREPARED,
            authority_source="user-confirmed erroneous duplicate 2026-08-30",
            exact_identity=True,
            quantitative_authority=False,
            composition_complete=True,
            authority_notes=("rejected current-stock claim",),
        ),
        ExactStockRef(
            exact_stock_ref=("inventory:historical:ambrofix-liquid:7.27pct-ww-heterogeneous"),
            material_name="Ambrofix",
            availability=StockAvailability.HISTORICAL_ONLY,
            fraction=0.0727,
            fraction_basis="w/w_whole_bottle_nominal",
            carrier="DEP + ethanol",
            aliquot_state=AliquotState.HETEROGENEOUS,
            authority_source="historical whole-bottle provenance 2026-08-29",
            exact_identity=True,
            quantitative_authority=False,
            composition_complete=True,
            authority_notes=(
                "liquid phase is not current executable stock",
                "visible-crystal provenance retained only",
            ),
        ),
        ExactStockRef(
            exact_stock_ref="inventory:v7:ambrofix-crystals:solid",
            material_name="Ambrofix Crystals",
            availability=StockAvailability.OWNED,
            fraction=1.0,
            fraction_basis="solid_mass",
            carrier="none",
            aliquot_state=AliquotState.READY,
            authority_source="inventory.txt distinct solid stock 2026-08-30",
            exact_identity=True,
            quantitative_authority=True,
            composition_complete=True,
            authority_notes=("not equivalent to historical liquid phase",),
        ),
        ExactStockRef(
            exact_stock_ref="inventory:v7:castoreum-synthetic-6up07515:10pct-dep",
            material_name="Castoreum Synthetic",
            availability=StockAvailability.OWNED,
            fraction=0.10,
            fraction_basis="unspecified",
            carrier="DEP",
            aliquot_state=AliquotState.READY,
            authority_source="user stock correction 2026-08-30",
            exact_identity=True,
            quantitative_authority=False,
            composition_complete=True,
            authority_notes=("concentration basis unresolved; quantitative HOLD",),
        ),
        ExactStockRef(
            exact_stock_ref="inventory:v8:benzyl-salicylate:neat",
            material_name="Benzyl Salicylate",
            availability=StockAvailability.OWNED,
            fraction=1.0,
            fraction_basis="neat_as_supplied",
            carrier="none",
            aliquot_state=AliquotState.READY,
            authority_source=(
                "user back-in-stock correction 2026-09-01 with prior V5 "
                "neat-stock lineage"
            ),
            exact_identity=True,
            quantitative_authority=True,
            composition_complete=True,
            authority_notes=(
                "availability reconfirmed on 2026-09-01",
                "stock form inherited from prior V5 neat/as-supplied record",
                (
                    "no supplier, purity, density, sensory, safety, stability, "
                    "liking, or release authority"
                ),
            ),
        ),
        ExactStockRef(
            exact_stock_ref="inventory:v8:bacdanol:neat",
            material_name="Bacdanol",
            availability=StockAvailability.OWNED,
            fraction=1.0,
            fraction_basis="neat_as_supplied",
            carrier="none",
            aliquot_state=AliquotState.READY,
            authority_source="user neat-stock correction 2026-09-01",
            exact_identity=True,
            quantitative_authority=True,
            composition_complete=True,
            authority_notes=(
                "ample neat stock",
                "stock strength does not assert supplier purity or sensory performance",
            ),
        ),
        ExactStockRef(
            exact_stock_ref="inventory:v7:clearwood:neat",
            material_name="Clearwood",
            availability=StockAvailability.OWNED,
            fraction=1.0,
            fraction_basis="neat_as_supplied",
            carrier="none",
            aliquot_state=AliquotState.READY,
            authority_source="user reconfirmation 2026-08-29",
            exact_identity=True,
            quantitative_authority=True,
            composition_complete=True,
        ),
        ExactStockRef(
            exact_stock_ref="inventory:v8:guaiacwood-eo:one-third-ww",
            material_name="Guaiacwood EO",
            availability=StockAvailability.OWNED,
            fraction=1.0 / 3.0,
            fraction_basis="mass_fraction",
            carrier="ethanol + DEP",
            aliquot_state=AliquotState.READY,
            authority_source="user exact one-third w/w correction 2026-09-01",
            exact_identity=True,
            quantitative_authority=True,
            composition_complete=True,
            authority_notes=(
                "exactly one-third Guaiacwood EO by mass",
                "remaining two-thirds are equal mass fractions of ethanol and DEP",
                "natural constituent composition and botanical identity remain unasserted",
            ),
        ),
    )
    return tuple(sorted(records, key=lambda item: item.exact_stock_ref))


__all__ = [
    "AliquotState",
    "ExactStockRef",
    "IdealMaterialSelection",
    "IdealProposal",
    "InventoryProjection",
    "InventoryProjectionLine",
    "ProjectionDisposition",
    "StockAvailability",
    "current_inventory_stock_corrections",
    "project_ideal_to_current_build",
]
