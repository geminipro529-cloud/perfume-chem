"""Runtime join for the V5 workbook, user inventory overlay, and exact stocks.

The workbook establishes the material/requirement register.  The dated user
overlay may update current physical ownership without rewriting that workbook.
An exact stock reference is a third, independent input.  Ownership therefore
never implies that a bottle, lot, carrier, or concentration basis has been
bound for physical execution.

This module grants no formula-rebase, substitution, molecular-mechanism,
sensory, safety, stability, or release authority.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from openpyxl import load_workbook

CURRENT_MASTER_SHEET = "Current Inventory Master"
ALIASES_SHEET = "Aliases and Non-Equivalents"
CURRENT_MASTER_HEADER_ROW = 5
ALIASES_HEADER_ROW = 5

_CURRENT_HEADERS = (
    "Canonical material",
    "Status",
    "Actual stock(s)",
    "Can prepare",
    "Family",
    "Alias / non-equivalent",
    "Formula-use policy",
    "User note",
)
_ALIAS_HEADERS = (
    "Material / name",
    "Compared with",
    "Relationship",
    "Required handling",
    "Reason",
    "Formula consequence",
)
_SAFE_ALIAS_RELATIONSHIPS = frozenset(
    {
        "DUPLICATE",
        "CANONICAL IDENTITY",
        "DEFINED DILUTION",
        "CANONICAL BOTANICAL MAPPING",
        "ACCEPTABLE GENERIC MAPPING",
        "SPELLING NORMALIZATION",
        "LEGACY SPELLING NORMALIZATION",
    }
)
_FORBIDDEN_ALIAS_RELATIONSHIPS = frozenset(
    {
        "NOT EQUIVALENT",
        "UNVERIFIED",
        "BANNED",
        "FUNCTIONAL ACCORD ONLY",
        "SPECIES-SPECIFIC SUBSTITUTE",
        "LABEL-NAME HOLD",
        "NOT MERGED",
        "PRODUCT BASIS",
    }
)


class InventoryAuthorityError(ValueError):
    """Raised when independently authoritative inventory inputs conflict."""


class InventoryAvailabilityState(str, Enum):
    OWNED = "OWNED"
    UNAVAILABLE = "UNAVAILABLE"
    PLANNED_ACQUISITION = "PLANNED_ACQUISITION"
    PREPARABLE = "PREPARABLE"
    VERIFY = "VERIFY"
    FORBIDDEN = "FORBIDDEN"
    UNLISTED = "UNLISTED"


class StockFractionBasis(str, Enum):
    NEAT = "neat"
    MASS_FRACTION = "mass_fraction"
    VOLUME_FRACTION = "volume_fraction"
    PRODUCT_BASIS = "product_basis"
    UNSPECIFIED = "unspecified"
    UNKNOWN = "unknown"


class StockFractionScope(str, Enum):
    """Physical scope to which a declared stock fraction applies."""

    UNSPECIFIED = "unspecified"
    HOMOGENEOUS_STOCK = "homogeneous_stock"
    WHOLE_BOTTLE_INCLUDING_SOLID = "whole_bottle_including_solid"


class StockHomogeneityState(str, Enum):
    """Whether a liquid aliquot may represent the declared stock fraction."""

    UNSPECIFIED = "unspecified"
    VERIFIED_CLEAR_STABLE = "verified_clear_stable"
    HOLD_VISIBLE_CRYSTALS = "hold_visible_crystals"


def _clean_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InventoryAuthorityError(f"{field} must be nonblank text")
    return " ".join(value.split())


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split())
    return text or None


def _key(value: object) -> str:
    return _clean_text(value, "material identity").casefold()


def _decimal(value: object, field: str) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise InventoryAuthorityError(f"{field} must be numeric")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise InventoryAuthorityError(f"{field} must be numeric") from error
    if not result.is_finite():
        raise InventoryAuthorityError(f"{field} must be finite")
    return result


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _headers(sheet: Any, row: int, required: tuple[str, ...]) -> dict[str, int]:
    values = next(sheet.iter_rows(min_row=row, max_row=row, values_only=True), None)
    if values is None:
        raise InventoryAuthorityError(f"{sheet.title} is missing header row {row}")
    indexes = {
        str(value).strip(): index
        for index, value in enumerate(values)
        if value is not None and str(value).strip()
    }
    missing = tuple(name for name in required if name not in indexes)
    if missing:
        raise InventoryAuthorityError(
            f"{sheet.title} is missing required headers: " + ", ".join(missing)
        )
    return indexes


@dataclass(frozen=True, slots=True)
class StockDefinition:
    fraction: Decimal | None
    fraction_basis: StockFractionBasis
    carrier: str | None
    fraction_authority: str
    execution_ready: bool
    fraction_scope: StockFractionScope = StockFractionScope.UNSPECIFIED
    homogeneity_state: StockHomogeneityState = StockHomogeneityState.UNSPECIFIED
    density_g_ml: Decimal | None = None

    def __post_init__(self) -> None:
        if self.fraction is not None and not (Decimal("0") < self.fraction <= Decimal("1")):
            raise InventoryAuthorityError("stock fraction must be in (0, 1]")
        if self.fraction_basis is StockFractionBasis.NEAT and self.fraction != Decimal("1"):
            raise InventoryAuthorityError("neat stock must have fraction 1")
        if self.density_g_ml is not None and (
            not self.density_g_ml.is_finite() or self.density_g_ml <= Decimal("0")
        ):
            raise InventoryAuthorityError("stock density_g_ml must be positive and finite")
        if self.carrier is not None:
            object.__setattr__(self, "carrier", _clean_text(self.carrier, "carrier").casefold())
        object.__setattr__(
            self,
            "fraction_authority",
            _clean_text(self.fraction_authority, "fraction_authority"),
        )

    @property
    def active_equivalence_authorized(self) -> bool:
        return (
            self.fraction is not None
            and self.fraction_basis
            in {StockFractionBasis.NEAT, StockFractionBasis.MASS_FRACTION}
            and self.fraction_scope
            is not StockFractionScope.WHOLE_BOTTLE_INCLUDING_SOLID
            and self.homogeneity_state
            is not StockHomogeneityState.HOLD_VISIBLE_CRYSTALS
        )

    @property
    def liquid_phase_execution_ready(self) -> bool:
        return (
            self.execution_ready
            and self.fraction_scope
            is not StockFractionScope.WHOLE_BOTTLE_INCLUDING_SOLID
            and self.homogeneity_state
            is not StockHomogeneityState.HOLD_VISIBLE_CRYSTALS
        )

    @property
    def volume_dose_math_ready(self) -> bool:
        return self.liquid_phase_execution_ready and self.density_g_ml is not None

    @property
    def molecular_mechanism_authority(self) -> bool:
        return False

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> StockDefinition:
        try:
            basis = StockFractionBasis(
                _clean_text(value.get("fraction_basis"), "fraction_basis").casefold()
            )
        except ValueError as error:
            raise InventoryAuthorityError("unsupported stock fraction_basis") from error
        try:
            fraction_scope = StockFractionScope(
                str(value.get("fraction_scope", StockFractionScope.UNSPECIFIED.value))
                .strip()
                .casefold()
            )
        except ValueError as error:
            raise InventoryAuthorityError("unsupported stock fraction_scope") from error
        try:
            homogeneity_state = StockHomogeneityState(
                str(
                    value.get(
                        "homogeneity_state", StockHomogeneityState.UNSPECIFIED.value
                    )
                )
                .strip()
                .casefold()
            )
        except ValueError as error:
            raise InventoryAuthorityError("unsupported stock homogeneity_state") from error
        fraction_value = value.get("fraction")
        density_value = value.get("density_g_ml")
        return cls(
            fraction=(
                _decimal(fraction_value, "stock fraction")
                if fraction_value is not None
                else None
            ),
            fraction_basis=basis,
            carrier=_optional_text(value.get("carrier")),
            fraction_authority=_clean_text(
                value.get("fraction_authority"), "fraction_authority"
            ),
            execution_ready=bool(value.get("execution_ready", False)),
            fraction_scope=fraction_scope,
            homogeneity_state=homogeneity_state,
            density_g_ml=(
                _decimal(density_value, "stock density_g_ml")
                if density_value is not None
                else None
            ),
        )


def _infer_stock(actual_stock: str | None, status: str) -> StockDefinition | None:
    text = " ".join(part for part in (actual_stock, status) if part)
    if not text:
        return None
    lowered = text.casefold()
    carrier_match = re.search(r"\bin\s+(dpg|dep|tec|ipm|ethanol)\b", lowered)
    carrier = carrier_match.group(1) if carrier_match else None
    percent_match = re.search(r"(?<![\d.])(\d+(?:\.\d+)?)\s*%", lowered)
    if percent_match:
        fraction = Decimal(percent_match.group(1)) / Decimal("100")
        if "w/w" in lowered or "mass fraction" in lowered:
            basis = StockFractionBasis.MASS_FRACTION
        elif "v/v" in lowered or "volume fraction" in lowered:
            basis = StockFractionBasis.VOLUME_FRACTION
        else:
            basis = StockFractionBasis.UNSPECIFIED
        return StockDefinition(
            fraction=fraction,
            fraction_basis=basis,
            carrier=carrier,
            fraction_authority="WORKBOOK_LABEL_TEXT",
            execution_ready=True,
        )
    if "neat" in lowered or "neat/as supplied" in lowered:
        return StockDefinition(
            fraction=Decimal("1"),
            fraction_basis=StockFractionBasis.NEAT,
            carrier=None,
            fraction_authority="WORKBOOK_EXPLICIT_NEAT_TEXT",
            execution_ready=True,
        )
    return StockDefinition(
        fraction=None,
        fraction_basis=StockFractionBasis.PRODUCT_BASIS,
        carrier=carrier,
        fraction_authority="WORKBOOK_OPAQUE_PRODUCT_TEXT",
        execution_ready=False,
    )


def _workbook_state(status: str) -> InventoryAvailabilityState:
    upper = status.upper()
    if upper.startswith("BANNED") or upper.startswith("DO NOT USE"):
        return InventoryAvailabilityState.FORBIDDEN
    if upper.startswith("OUT OF STOCK") or upper.startswith("GAP") or upper.startswith("MISSING"):
        return InventoryAvailabilityState.UNAVAILABLE
    if upper.startswith("PLANNED ACQUISITION"):
        return InventoryAvailabilityState.PLANNED_ACQUISITION
    if upper.startswith("CONSTRUCTIBLE") or "PREPARATION REQUIRED" in upper:
        return InventoryAvailabilityState.PREPARABLE
    if upper.startswith("VERIFY"):
        return InventoryAvailabilityState.VERIFY
    if upper.startswith("HAVE"):
        return InventoryAvailabilityState.OWNED
    return InventoryAvailabilityState.VERIFY


@dataclass(frozen=True, slots=True)
class WorkbookInventoryRecord:
    source_row: int
    canonical_name: str
    state: InventoryAvailabilityState
    status: str
    actual_stock_text: str | None
    can_prepare: str | None
    family: str | None
    alias_or_non_equivalent: str | None
    formula_use_policy: str | None
    user_note: str | None
    stock: StockDefinition | None


@dataclass(frozen=True, slots=True)
class WorkbookAliasRecord:
    source_row: int
    material: str
    compared_with: str
    relationship: str
    required_handling: str | None
    reason: str | None
    formula_consequence: str | None


@dataclass(frozen=True, slots=True)
class OverlayInventoryRecord:
    record_id: str
    canonical_name: str
    aliases: tuple[str, ...]
    state: str
    category: str
    stock: StockDefinition | None
    supersedes_parent_rows: tuple[int, ...]
    requirement_overrides: tuple[Mapping[str, Any], ...]
    physical_evidence: Mapping[str, Any]
    authority_boundaries: tuple[str, ...]
    note: str


@dataclass(frozen=True, slots=True)
class SensorySubstitutionAuthority:
    substitution_id: str
    protocol_id: str
    source_material: str
    source_dose_ul: Decimal
    replacement_material: str
    replacement_dose_ul: Decimal
    working_stock_fraction: Decimal
    working_stock_dose_ul: Decimal
    working_stock_recipe: str
    sensory_substitution_authority: bool
    chemical_equivalence_authority: bool
    oav_equivalence_authority: bool
    safety_authority: bool
    stability_authority: bool
    general_formula_authority: bool

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> SensorySubstitutionAuthority:
        authority = value.get("authority")
        if not isinstance(authority, Mapping):
            raise InventoryAuthorityError("sensory substitution authority must be a mapping")
        result = cls(
            substitution_id=_clean_text(value.get("substitution_id"), "substitution_id"),
            protocol_id=_clean_text(value.get("protocol_id"), "protocol_id"),
            source_material=_clean_text(value.get("source_material"), "source_material"),
            source_dose_ul=_decimal(value.get("source_dose_ul"), "source_dose_ul"),
            replacement_material=_clean_text(
                value.get("replacement_material"), "replacement_material"
            ),
            replacement_dose_ul=_decimal(
                value.get("replacement_dose_ul"), "replacement_dose_ul"
            ),
            working_stock_fraction=_decimal(
                value.get("working_stock_fraction"), "working_stock_fraction"
            ),
            working_stock_dose_ul=_decimal(
                value.get("working_stock_dose_ul"), "working_stock_dose_ul"
            ),
            working_stock_recipe=_clean_text(
                value.get("working_stock_recipe"), "working_stock_recipe"
            ),
            sensory_substitution_authority=bool(
                authority.get("sensory_substitution_authority", False)
            ),
            chemical_equivalence_authority=bool(
                authority.get("chemical_equivalence_authority", False)
            ),
            oav_equivalence_authority=bool(
                authority.get("oav_equivalence_authority", False)
            ),
            safety_authority=bool(authority.get("safety_authority", False)),
            stability_authority=bool(authority.get("stability_authority", False)),
            general_formula_authority=bool(
                authority.get("general_formula_authority", False)
            ),
        )
        if result.protocol_id != "AP-T1":
            raise InventoryAuthorityError("sensory substitution must remain AP-T1 scoped")
        if result.replacement_dose_ul >= Decimal("10"):
            raise InventoryAuthorityError("AP-T1 replacement must document the sub-10 uL dose")
        if result.working_stock_dose_ul < Decimal("10"):
            raise InventoryAuthorityError("AP-T1 working-stock dose must meet the 10 uL floor")
        if result.working_stock_fraction != Decimal("0.03"):
            raise InventoryAuthorityError("AP-T1 working stock must be nominal 3%")
        prohibited = (
            result.chemical_equivalence_authority,
            result.oav_equivalence_authority,
            result.safety_authority,
            result.stability_authority,
            result.general_formula_authority,
        )
        if not result.sensory_substitution_authority or any(prohibited):
            raise InventoryAuthorityError("AP-T1 authority flags exceed exact sensory scope")
        return result


class UserInventoryOverlay:
    def __init__(self, payload: Mapping[str, Any], source_sha256: str) -> None:
        if payload.get("schema_version") != "perfume_chem_user_inventory_authority_overlay_v1":
            raise InventoryAuthorityError("unsupported user inventory overlay schema")
        if payload.get("authority") != "USER_CURRENT_PHYSICAL_INVENTORY_AUTHORITY":
            raise InventoryAuthorityError("overlay lacks user current-inventory authority")
        self.source_sha256 = source_sha256
        self.effective_date = _clean_text(payload.get("effective_date"), "effective_date")
        parent = payload.get("parent")
        if not isinstance(parent, Mapping):
            raise InventoryAuthorityError("overlay parent must be a mapping")
        self.parent_workbook_sha256 = _clean_text(
            parent.get("workbook_sha256"), "parent workbook_sha256"
        ).casefold()
        if not re.fullmatch(r"[0-9a-f]{64}", self.parent_workbook_sha256):
            raise InventoryAuthorityError("parent workbook_sha256 must be SHA-256 hex")
        policy = payload.get("policy")
        if not isinstance(policy, Mapping):
            raise InventoryAuthorityError("overlay policy must be a mapping")
        self.policy = MappingProxyType(dict(policy))

        raw_records = payload.get("records")
        if not isinstance(raw_records, list):
            raise InventoryAuthorityError("overlay records must be a list")
        records: list[OverlayInventoryRecord] = []
        by_key: dict[str, OverlayInventoryRecord] = {}
        aliases: dict[str, str] = {}
        for raw in raw_records:
            if not isinstance(raw, Mapping):
                raise InventoryAuthorityError("overlay record must be a mapping")
            raw_aliases = raw.get("aliases", [])
            if not isinstance(raw_aliases, list):
                raise InventoryAuthorityError("overlay aliases must be a list")
            raw_stock = raw.get("stock")
            if raw_stock is not None and not isinstance(raw_stock, Mapping):
                raise InventoryAuthorityError("overlay stock must be a mapping or null")
            supersedes = raw.get("supersedes_parent_stocks", [])
            if not isinstance(supersedes, list):
                raise InventoryAuthorityError("supersedes_parent_stocks must be a list")
            superseded_rows = tuple(
                int(item["source_row"])
                for item in supersedes
                if isinstance(item, Mapping) and "source_row" in item
            )
            overrides = raw.get("requirement_overrides", [])
            if not isinstance(overrides, list) or any(
                not isinstance(item, Mapping) for item in overrides
            ):
                raise InventoryAuthorityError("requirement_overrides must be mappings")
            physical_evidence = raw.get("physical_evidence", {})
            if not isinstance(physical_evidence, Mapping):
                raise InventoryAuthorityError("physical_evidence must be a mapping")
            authority_boundaries = raw.get("authority_boundaries", [])
            if not isinstance(authority_boundaries, list):
                raise InventoryAuthorityError("authority_boundaries must be a list")
            record = OverlayInventoryRecord(
                record_id=_clean_text(raw.get("record_id"), "record_id"),
                canonical_name=_clean_text(raw.get("canonical_name"), "canonical_name"),
                aliases=tuple(_clean_text(item, "alias") for item in raw_aliases),
                state=_clean_text(raw.get("state"), "state").upper(),
                category=_clean_text(raw.get("category"), "category"),
                stock=StockDefinition.from_mapping(raw_stock) if raw_stock else None,
                supersedes_parent_rows=superseded_rows,
                requirement_overrides=tuple(MappingProxyType(dict(item)) for item in overrides),
                physical_evidence=MappingProxyType(dict(physical_evidence)),
                authority_boundaries=tuple(
                    _clean_text(item, "authority boundary")
                    for item in authority_boundaries
                ),
                note=_clean_text(raw.get("note"), "note"),
            )
            canonical_key = _key(record.canonical_name)
            if canonical_key in by_key:
                raise InventoryAuthorityError(
                    f"duplicate overlay material: {record.canonical_name}"
                )
            by_key[canonical_key] = record
            records.append(record)
            for alias in record.aliases:
                alias_key = _key(alias)
                prior = aliases.get(alias_key)
                if prior is not None and prior != canonical_key:
                    raise InventoryAuthorityError(f"overlay alias collision: {alias}")
                aliases[alias_key] = canonical_key
        self.records = tuple(records)
        self._by_key = MappingProxyType(by_key)
        self._aliases = MappingProxyType(aliases)

        raw_substitutions = payload.get("sensory_substitutions", [])
        if not isinstance(raw_substitutions, list):
            raise InventoryAuthorityError("sensory_substitutions must be a list")
        substitutions = tuple(
            SensorySubstitutionAuthority.from_mapping(item)
            for item in raw_substitutions
            if isinstance(item, Mapping)
        )
        self.sensory_substitutions = substitutions
        self._substitutions = MappingProxyType(
            {item.substitution_id: item for item in substitutions}
        )

    def identity_for(self, material: str) -> str:
        requested_key = _key(material)
        canonical_key = self._aliases.get(requested_key, requested_key)
        record = self._by_key.get(canonical_key)
        return record.canonical_name if record is not None else _clean_text(material, "material")

    def record(self, material: str) -> OverlayInventoryRecord:
        canonical = self.identity_for(material)
        try:
            return self._by_key[_key(canonical)]
        except KeyError as error:
            raise KeyError(material) from error

    def sensory_substitution(self, substitution_id: str) -> SensorySubstitutionAuthority:
        try:
            return self._substitutions[_clean_text(substitution_id, "substitution_id")]
        except KeyError as error:
            raise KeyError(substitution_id) from error


def load_user_inventory_overlay(path: str | Path) -> UserInventoryOverlay:
    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise InventoryAuthorityError("user overlay root must be a mapping")
    return UserInventoryOverlay(payload, _sha256(source))


def _parse_workbook(
    workbook_path: Path,
) -> tuple[tuple[WorkbookInventoryRecord, ...], tuple[WorkbookAliasRecord, ...]]:
    workbook = load_workbook(workbook_path, read_only=True, data_only=True)
    try:
        for required_sheet in (CURRENT_MASTER_SHEET, ALIASES_SHEET):
            if required_sheet not in workbook.sheetnames:
                raise InventoryAuthorityError(
                    f"inventory workbook is missing {required_sheet}"
                )
        current_sheet = workbook[CURRENT_MASTER_SHEET]
        current_headers = _headers(
            current_sheet, CURRENT_MASTER_HEADER_ROW, _CURRENT_HEADERS
        )
        records: list[WorkbookInventoryRecord] = []
        for source_row, values in enumerate(
            current_sheet.iter_rows(
                min_row=CURRENT_MASTER_HEADER_ROW + 1, values_only=True
            ),
            start=CURRENT_MASTER_HEADER_ROW + 1,
        ):
            canonical_value = (
                values[current_headers["Canonical material"]]
                if current_headers["Canonical material"] < len(values)
                else None
            )
            canonical_name = _optional_text(canonical_value)
            if canonical_name is None:
                continue
            def value(header: str) -> str | None:
                index = current_headers[header]
                return _optional_text(values[index] if index < len(values) else None)

            status = value("Status")
            if status is None:
                raise InventoryAuthorityError(
                    f"Current Inventory Master row {source_row} lacks status"
                )
            actual_stock = value("Actual stock(s)")
            records.append(
                WorkbookInventoryRecord(
                    source_row=source_row,
                    canonical_name=canonical_name,
                    state=_workbook_state(status),
                    status=status,
                    actual_stock_text=actual_stock,
                    can_prepare=value("Can prepare"),
                    family=value("Family"),
                    alias_or_non_equivalent=value("Alias / non-equivalent"),
                    formula_use_policy=value("Formula-use policy"),
                    user_note=value("User note"),
                    stock=_infer_stock(actual_stock, status),
                )
            )

        alias_sheet = workbook[ALIASES_SHEET]
        alias_headers = _headers(alias_sheet, ALIASES_HEADER_ROW, _ALIAS_HEADERS)
        aliases: list[WorkbookAliasRecord] = []
        for source_row, values in enumerate(
            alias_sheet.iter_rows(min_row=ALIASES_HEADER_ROW + 1, values_only=True),
            start=ALIASES_HEADER_ROW + 1,
        ):
            left = _optional_text(
                values[alias_headers["Material / name"]]
                if alias_headers["Material / name"] < len(values)
                else None
            )
            right = _optional_text(
                values[alias_headers["Compared with"]]
                if alias_headers["Compared with"] < len(values)
                else None
            )
            relationship = _optional_text(
                values[alias_headers["Relationship"]]
                if alias_headers["Relationship"] < len(values)
                else None
            )
            if left is None and right is None and relationship is None:
                continue
            if left is None or right is None or relationship is None:
                raise InventoryAuthorityError(
                    f"Aliases and Non-Equivalents row {source_row} is incomplete"
                )
            def alias_value(header: str) -> str | None:
                index = alias_headers[header]
                return _optional_text(values[index] if index < len(values) else None)

            aliases.append(
                WorkbookAliasRecord(
                    source_row=source_row,
                    material=left,
                    compared_with=right,
                    relationship=relationship,
                    required_handling=alias_value("Required handling"),
                    reason=alias_value("Reason"),
                    formula_consequence=alias_value("Formula consequence"),
                )
            )
        return tuple(records), tuple(aliases)
    finally:
        workbook.close()


def _override_state(disposition: str) -> InventoryAvailabilityState:
    normalized = disposition.upper()
    if normalized == "OWNED":
        return InventoryAvailabilityState.OWNED
    if normalized in {"GAP", "UNAVAILABLE", "OUT_OF_STOCK"}:
        return InventoryAvailabilityState.UNAVAILABLE
    if normalized in {"PREPARATION_REQUIRED", "PREPARABLE"}:
        return InventoryAvailabilityState.PREPARABLE
    if normalized == "VERIFY":
        return InventoryAvailabilityState.VERIFY
    raise InventoryAuthorityError(f"unsupported requirement disposition: {disposition}")


@dataclass(frozen=True, slots=True)
class InventoryAuthorityProjection:
    requested_name: str
    canonical_name: str
    state: InventoryAvailabilityState
    stock: StockDefinition | None
    exact_stock_ref: str | None
    physical_execution_ready: bool
    active_equivalence_ready: bool
    molecular_mechanism_authority: bool
    formula_rebase_authorized: bool
    general_substitution_authorized: bool
    source_rows: tuple[int, ...]
    status: str
    note: str | None


class InventoryAuthoritySnapshot:
    def __init__(
        self,
        *,
        workbook_sha256: str,
        overlay: UserInventoryOverlay,
        workbook_records: tuple[WorkbookInventoryRecord, ...],
        alias_records: tuple[WorkbookAliasRecord, ...],
        records: Mapping[str, InventoryAuthorityProjection],
        aliases: Mapping[str, str],
        forbidden_pairs: frozenset[frozenset[str]],
    ) -> None:
        self.workbook_sha256 = workbook_sha256
        self.overlay_sha256 = overlay.source_sha256
        self.workbook_record_count = len(workbook_records)
        self.alias_record_count = len(alias_records)
        self.formula_rebase_authorized = bool(
            overlay.policy.get("formula_rebase_authorized", False)
        )
        self.general_substitution_authorized = bool(
            overlay.policy.get("general_substitution_authorized", False)
        )
        self._records = MappingProxyType(dict(records))
        self._aliases = MappingProxyType(dict(aliases))
        self._forbidden_pairs = forbidden_pairs

    def project(self, material: str) -> InventoryAuthorityProjection:
        requested = _clean_text(material, "material")
        requested_key = _key(requested)
        canonical_key = self._aliases.get(requested_key, requested_key)
        record = self._records.get(canonical_key)
        if record is None:
            return InventoryAuthorityProjection(
                requested_name=requested,
                canonical_name=requested,
                state=InventoryAvailabilityState.UNLISTED,
                stock=None,
                exact_stock_ref=None,
                physical_execution_ready=False,
                active_equivalence_ready=False,
                molecular_mechanism_authority=False,
                formula_rebase_authorized=False,
                general_substitution_authorized=False,
                source_rows=(),
                status="UNLISTED",
                note=None,
            )
        return replace(record, requested_name=requested)

    def is_forbidden_equivalence(self, left: str, right: str) -> bool:
        return frozenset((_key(left), _key(right))) in self._forbidden_pairs


def load_inventory_authority_snapshot(
    workbook_path: str | Path,
    overlay_path: str | Path,
    *,
    exact_stock_refs: Mapping[str, Mapping[str, Any]] | None = None,
) -> InventoryAuthoritySnapshot:
    workbook_source = Path(workbook_path)
    workbook_sha256 = _sha256(workbook_source)
    overlay = load_user_inventory_overlay(overlay_path)
    if workbook_sha256 != overlay.parent_workbook_sha256:
        raise InventoryAuthorityError(
            "inventory workbook hash does not match the overlay parent authority"
        )
    workbook_records, alias_records = _parse_workbook(workbook_source)

    mutable_by_key: dict[str, InventoryAuthorityProjection] = {}
    row_to_key: dict[int, str] = {}
    for item in workbook_records:
        canonical_key = _key(item.canonical_name)
        if canonical_key in mutable_by_key:
            raise InventoryAuthorityError(
                f"duplicate current inventory material: {item.canonical_name}"
            )
        row_to_key[item.source_row] = canonical_key
        mutable_by_key[canonical_key] = InventoryAuthorityProjection(
            requested_name=item.canonical_name,
            canonical_name=item.canonical_name,
            state=item.state,
            stock=item.stock,
            exact_stock_ref=None,
            physical_execution_ready=False,
            active_equivalence_ready=False,
            molecular_mechanism_authority=False,
            formula_rebase_authorized=False,
            general_substitution_authorized=False,
            source_rows=(item.source_row,),
            status=item.status,
            note=item.formula_use_policy or item.user_note,
        )

    aliases: dict[str, str] = {}
    forbidden_pairs: set[frozenset[str]] = set()
    for item in alias_records:
        left = _key(item.material)
        right = _key(item.compared_with)
        relationship = item.relationship.upper()
        if relationship in _SAFE_ALIAS_RELATIONSHIPS:
            if right in mutable_by_key:
                aliases[left] = right
            elif left in mutable_by_key:
                aliases[right] = left
        if relationship in _FORBIDDEN_ALIAS_RELATIONSHIPS:
            forbidden_pairs.add(frozenset((left, right)))

    for overlay_record in overlay.records:
        for source_row in overlay_record.supersedes_parent_rows:
            parent_key = row_to_key.get(source_row)
            if parent_key is None:
                raise InventoryAuthorityError(
                    f"overlay supersedes missing workbook row {source_row}"
                )
            parent = mutable_by_key[parent_key]
            mutable_by_key[parent_key] = replace(
                parent,
                state=InventoryAvailabilityState.UNAVAILABLE,
                stock=None,
                status="SUPERSEDED BY USER AUTHORITY OVERLAY",
                note=overlay_record.note,
            )
        for raw_override in overlay_record.requirement_overrides:
            source_row = raw_override.get("source_row")
            if not isinstance(source_row, int) or source_row not in row_to_key:
                raise InventoryAuthorityError(
                    f"overlay requirement override references missing row {source_row}"
                )
            requirement_key = row_to_key[source_row]
            requirement = mutable_by_key[requirement_key]
            disposition = _clean_text(
                raw_override.get("disposition"), "requirement disposition"
            )
            status = _clean_text(raw_override.get("status"), "requirement status")
            actual_stock_text = _optional_text(raw_override.get("actual_stock_text"))
            mutable_by_key[requirement_key] = replace(
                requirement,
                state=_override_state(disposition),
                stock=_infer_stock(actual_stock_text, status),
                status=status,
                note=overlay_record.note,
            )

        canonical_key = _key(overlay_record.canonical_name)
        existing = mutable_by_key.get(canonical_key)
        if overlay_record.state == "IDENTITY_ALIAS":
            if existing is None:
                mutable_by_key[canonical_key] = InventoryAuthorityProjection(
                    requested_name=overlay_record.canonical_name,
                    canonical_name=overlay_record.canonical_name,
                    state=InventoryAvailabilityState.UNLISTED,
                    stock=None,
                    exact_stock_ref=None,
                    physical_execution_ready=False,
                    active_equivalence_ready=False,
                    molecular_mechanism_authority=False,
                    formula_rebase_authorized=False,
                    general_substitution_authorized=False,
                    source_rows=(),
                    status="IDENTITY ALIAS ONLY",
                    note=overlay_record.note,
                )
        else:
            state_map = {
                "OWNED": InventoryAvailabilityState.OWNED,
                "UNAVAILABLE": InventoryAvailabilityState.UNAVAILABLE,
                "PLANNED_ACQUISITION": InventoryAvailabilityState.PLANNED_ACQUISITION,
                "VERIFY": InventoryAvailabilityState.VERIFY,
            }
            try:
                overlay_state = state_map[overlay_record.state]
            except KeyError as error:
                raise InventoryAuthorityError(
                    f"unsupported overlay state: {overlay_record.state}"
                ) from error
            mutable_by_key[canonical_key] = InventoryAuthorityProjection(
                requested_name=overlay_record.canonical_name,
                canonical_name=overlay_record.canonical_name,
                state=overlay_state,
                stock=overlay_record.stock if overlay_state is InventoryAvailabilityState.OWNED else None,
                exact_stock_ref=None,
                physical_execution_ready=False,
                active_equivalence_ready=False,
                molecular_mechanism_authority=False,
                formula_rebase_authorized=False,
                general_substitution_authorized=False,
                source_rows=existing.source_rows if existing is not None else (),
                status=f"USER OVERLAY {overlay_record.state}",
                note=overlay_record.note,
            )
        for alias in overlay_record.aliases:
            alias_key = _key(alias)
            prior = aliases.get(alias_key)
            if prior is not None and prior != canonical_key:
                raise InventoryAuthorityError(f"inventory alias collision: {alias}")
            aliases[alias_key] = canonical_key

    if not bool(overlay.policy.get("unlisted_tinctures_available", False)):
        for canonical_key, record in tuple(mutable_by_key.items()):
            if "tincture" in record.canonical_name.casefold():
                mutable_by_key[canonical_key] = replace(
                    record,
                    state=InventoryAvailabilityState.UNAVAILABLE,
                    stock=None,
                    exact_stock_ref=None,
                    physical_execution_ready=False,
                    active_equivalence_ready=False,
                    status="OUT OF STOCK - ALL TINCTURES LOST",
                    note="User current-inventory authority, effective 2026-08-28.",
                )

    seen_stock_refs: set[str] = set()
    for requested_name, raw_ref in (exact_stock_refs or {}).items():
        requested_key = _key(requested_name)
        canonical_key = aliases.get(requested_key, requested_key)
        record = mutable_by_key.get(canonical_key)
        if record is None:
            raise InventoryAuthorityError(
                f"exact stock references unlisted identity: {requested_name}"
            )
        if record.state is not InventoryAvailabilityState.OWNED or record.stock is None:
            raise InventoryAuthorityError(
                f"exact stock cannot bind unavailable identity: {requested_name}"
            )
        stock_ref = _clean_text(raw_ref.get("stock_ref"), "exact stock_ref")
        if stock_ref in seen_stock_refs:
            raise InventoryAuthorityError(f"duplicate exact stock_ref: {stock_ref}")
        seen_stock_refs.add(stock_ref)
        fraction = _decimal(raw_ref.get("fraction"), "exact stock fraction")
        try:
            basis = StockFractionBasis(
                _clean_text(
                    raw_ref.get("fraction_basis"), "exact stock fraction_basis"
                ).casefold()
            )
        except ValueError as error:
            raise InventoryAuthorityError("unsupported exact stock fraction_basis") from error
        carrier = _optional_text(raw_ref.get("carrier"))
        normalized_carrier = carrier.casefold() if carrier is not None else None
        if record.stock.fraction != fraction:
            raise InventoryAuthorityError(
                f"exact stock fraction conflicts with inventory authority for {requested_name}"
            )
        if record.stock.fraction_basis is not basis:
            raise InventoryAuthorityError(
                f"exact stock fraction basis conflicts with inventory authority for {requested_name}"
            )
        if record.stock.carrier != normalized_carrier:
            raise InventoryAuthorityError(
                f"exact stock carrier conflicts with inventory authority for {requested_name}"
            )
        physical_ready = record.stock.liquid_phase_execution_ready
        mutable_by_key[canonical_key] = replace(
            record,
            exact_stock_ref=stock_ref,
            physical_execution_ready=physical_ready,
            active_equivalence_ready=(
                physical_ready and record.stock.active_equivalence_authorized
            ),
        )

    return InventoryAuthoritySnapshot(
        workbook_sha256=workbook_sha256,
        overlay=overlay,
        workbook_records=workbook_records,
        alias_records=alias_records,
        records=mutable_by_key,
        aliases=aliases,
        forbidden_pairs=frozenset(forbidden_pairs),
    )
