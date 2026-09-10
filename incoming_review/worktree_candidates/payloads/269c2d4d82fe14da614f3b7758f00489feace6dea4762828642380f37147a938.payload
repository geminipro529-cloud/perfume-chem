"""Evidence-qualified capabilities for every current Perfume-Chem material.

The atlas joins three scopes without letting any one of them impersonate the
others:

* the immutable V5 workbook projection and its dated user overlay provide
  requirement and stock lineage;
* ``inventory.txt`` provides the latest consolidated current-stock state;
* the A-Z material spine provides field-level scientific hypotheses and
  provenance, never current-stock or liking authority.

No field in this module proves sensory behavior, liking, similarity, safety,
stability, compounding success, or release readiness.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Iterable

from engine.data_spine.loader import DEFAULT_DATA_DIR, load_registry
from engine.data_spine.material import Material
from engine.inventory_parser import (
    CURRENT_INVENTORY_SNAPSHOT_PATH,
    CURRENT_USER_INVENTORY_OVERLAY_PATH,
    INVENTORY_PATH,
    CurrentInventoryMaterialization,
    InventoryMaterial,
    materialize_current_inventory,
    parse_inventory,
)
from engine.material_identity import profile_canonical_name
from engine.name_utils import normalize_name


class InventoryCapabilityState(str, Enum):
    OWNED_EXECUTABLE = "OWNED_EXECUTABLE"
    OWNED_HELD = "OWNED_HELD"
    UNAVAILABLE = "UNAVAILABLE"
    UNLISTED = "UNLISTED"


class KnowledgeState(str, Enum):
    PROFILED = "PROFILED"
    PARTIAL_PROFILE = "PARTIAL_PROFILE"
    MISSING_PROFILE = "MISSING_PROFILE"


class MaterialClass(str, Enum):
    SINGLE_MOLECULE = "SINGLE_MOLECULE"
    NATURAL_MIXTURE = "NATURAL_MIXTURE"
    PROPRIETARY_BLEND = "PROPRIETARY_BLEND"
    UNRESOLVED = "UNRESOLVED"


class EvidenceGrade(str, Enum):
    PRIMARY_DATABASE = "PRIMARY_DATABASE"
    SOURCE_DOCUMENT = "SOURCE_DOCUMENT"
    SUPPLIER_CATALOG = "SUPPLIER_CATALOG"
    INTERNAL_MODEL = "INTERNAL_MODEL"
    UNSOURCED_LEGACY = "UNSOURCED_LEGACY"


@dataclass(frozen=True, slots=True)
class CapabilityEvidence:
    field_name: str
    value: str | float
    source_ref: str | None
    evidence_grade: EvidenceGrade


@dataclass(frozen=True, slots=True)
class StockCapability:
    raw_name: str
    status: str
    active_fraction: Decimal | None
    fraction_basis: str
    carrier: str | None
    execution_ready: bool
    hold_reason: str | None
    source: str = "CURRENT_CONSOLIDATED_USER_STOCK_TEXT"


@dataclass(frozen=True, slots=True)
class CapabilityConflict:
    field: str
    prior_value: str
    effective_value: str
    prior_source: str
    effective_source: str
    resolution: str


@dataclass(frozen=True, slots=True)
class MaterialCapabilityRecord:
    canonical_name: str
    identity_key: str
    categories: tuple[str, ...]
    inventory_state: InventoryCapabilityState
    current_stocks: tuple[StockCapability, ...]
    qualitative_selectable: bool
    quantitative_execution_ready: bool
    material_class: MaterialClass
    knowledge_state: KnowledgeState
    science_evidence: tuple[CapabilityEvidence, ...]
    contextual_functions: tuple[CapabilityEvidence, ...]
    temporal_registers: tuple[CapabilityEvidence, ...]
    interfaces: tuple[CapabilityEvidence, ...]
    takeover_modes: tuple[CapabilityEvidence, ...]
    hedonic_claims: tuple[CapabilityEvidence, ...]
    v5_source_rows: tuple[int, ...]
    v5_requirement_states: tuple[str, ...]
    conflicts: tuple[CapabilityConflict, ...]
    blockers: tuple[str, ...]
    legacy_hedonic_value_ignored: bool
    constituent_identity_authority: bool = field(default=False, init=False)
    composite_oav_authority: bool = field(default=False, init=False)
    sensory_authority: bool = field(default=False, init=False)
    liking_authority: bool = field(default=False, init=False)
    similarity_authority: bool = field(default=False, init=False)
    safety_authority: bool = field(default=False, init=False)
    stability_authority: bool = field(default=False, init=False)
    procurement_authority: bool = field(default=False, init=False)
    preparation_authority: bool = field(default=False, init=False)
    compounding_authority: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)

    def evidence_for(self, field_name: str) -> CapabilityEvidence | None:
        for item in self.science_evidence:
            if item.field_name == field_name:
                return item
        return None


class MaterialCapabilityAtlas:
    """Immutable, alias-aware projection over current material identities."""

    def __init__(
        self,
        *,
        records: Iterable[MaterialCapabilityRecord],
        current_stock_row_count: int,
        v5_stock_count: int,
        v5_requirement_count: int,
        inventory_text_sha256: str,
        v5_workbook_sha256: str,
        v5_snapshot_sha256: str,
        user_overlay_sha256: str,
        material_data_fingerprint: str,
    ) -> None:
        ordered = tuple(sorted(records, key=lambda item: item.canonical_name.casefold()))
        self.records = ordered
        self.current_stock_row_count = current_stock_row_count
        self.current_identity_count = len(ordered)
        self.v5_stock_count = v5_stock_count
        self.v5_requirement_count = v5_requirement_count
        self.inventory_text_sha256 = inventory_text_sha256
        self.v5_workbook_sha256 = v5_workbook_sha256
        self.v5_snapshot_sha256 = v5_snapshot_sha256
        self.user_overlay_sha256 = user_overlay_sha256
        self.material_data_fingerprint = material_data_fingerprint

        exact = {record.identity_key: record for record in ordered}
        normalized_candidates: dict[str, list[MaterialCapabilityRecord]] = {}
        for record in ordered:
            normalized_candidates.setdefault(
                normalize_name(record.canonical_name), []
            ).append(record)
        aliases = {
            key: values[0]
            for key, values in normalized_candidates.items()
            if len(values) == 1 and key not in exact
        }
        self._exact = exact
        self._aliases = aliases

    def project(self, material: str) -> MaterialCapabilityRecord:
        requested = " ".join(str(material).split())
        exact = self._exact.get(requested.casefold())
        if exact is not None:
            return exact
        normalized = normalize_name(requested)
        alias = self._exact.get(normalized) or self._aliases.get(normalized)
        if alias is not None:
            return alias
        return MaterialCapabilityRecord(
            canonical_name=requested,
            identity_key=requested.casefold(),
            categories=(),
            inventory_state=InventoryCapabilityState.UNLISTED,
            current_stocks=(),
            qualitative_selectable=False,
            quantitative_execution_ready=False,
            material_class=MaterialClass.UNRESOLVED,
            knowledge_state=KnowledgeState.MISSING_PROFILE,
            science_evidence=(),
            contextual_functions=(),
            temporal_registers=(),
            interfaces=(),
            takeover_modes=(),
            hedonic_claims=(),
            v5_source_rows=(),
            v5_requirement_states=(),
            conflicts=(),
            blockers=("MATERIAL_UNLISTED",),
            legacy_hedonic_value_ignored=False,
        )


def _normalized_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _data_fingerprint(data_dir: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(data_dir.glob("*.yaml"), key=lambda item: item.name):
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_bytes().replace(b"\r\n", b"\n"))
    return digest.hexdigest()


def _profile_lookup(materials: Iterable[Material]) -> dict[str, Material]:
    candidates: dict[str, list[Material]] = {}
    for material in materials:
        names = (material.canonical_name, *material.aliases)
        for name in names:
            candidates.setdefault(normalize_name(name), []).append(material)
    return {
        key: values[0]
        for key, values in candidates.items()
        if len({value.canonical_name.casefold() for value in values}) == 1
    }


def _find_profile(
    canonical_name: str,
    *,
    registry: Any,
    normalized_profiles: dict[str, Material],
) -> Material | None:
    direct = registry.get(canonical_name)
    if direct is not None:
        return direct
    profile_name = profile_canonical_name(canonical_name)
    if profile_name:
        direct = registry.get(profile_name)
        if direct is not None:
            return direct
    return normalized_profiles.get(normalize_name(canonical_name))


def _material_class(name: str, profile: Material | None) -> MaterialClass:
    key = name.casefold()
    natural_tokens = (
        " eo",
        "essential oil",
        " absolute",
        "resinoid",
        "tincture",
        "extract",
        "oil sicilian",
        "blossoms",
    )
    if any(token in f" {key}" for token in natural_tokens):
        return MaterialClass.NATURAL_MIXTURE
    blend_tokens = (
        " base",
        " ftec",
        " f-tec",
        " artificial",
        " fleuressence",
        " fo",
        "synthetic",
    )
    if any(token in f" {key}" for token in blend_tokens):
        return MaterialClass.PROPRIETARY_BLEND
    if profile is not None and (profile.cas or profile.smiles or profile.inchikey):
        return MaterialClass.SINGLE_MOLECULE
    return MaterialClass.UNRESOLVED


def _evidence_grade(source_ref: str | None) -> EvidenceGrade:
    if not source_ref:
        return EvidenceGrade.UNSOURCED_LEGACY
    source = source_ref.casefold()
    if "pubchem" in source or "nist" in source:
        return EvidenceGrade.PRIMARY_DATABASE
    if source.startswith("http") or "doi" in source:
        return EvidenceGrade.SOURCE_DOCUMENT
    if "perfumersworld" in source or "supplier" in source:
        return EvidenceGrade.SUPPLIER_CATALOG
    if source.startswith("engine.") or source.startswith("engine/"):
        return EvidenceGrade.INTERNAL_MODEL
    return EvidenceGrade.UNSOURCED_LEGACY


def _science_evidence(profile: Material | None) -> tuple[CapabilityEvidence, ...]:
    if profile is None:
        return ()
    fields = (
        ("cas", profile.cas, "cas"),
        ("smiles", profile.smiles, "smiles"),
        ("inchikey", profile.inchikey, "inchikey"),
        ("mw_g_mol", profile.mw_g_mol, "mw_g_mol"),
        ("density_25c_g_ml", profile.density_25c_g_ml, "density_25c_g_ml"),
        ("logp", profile.logp, "logp"),
        ("vp_25c_pa", profile.vp_25c_pa, "vp_25c_pa"),
        ("odt_air_ppb", profile.odt_air_ppb, "odt_air_ppb"),
        ("odt_eth_ppm", profile.odt_eth_ppm, "odt_eth_ppm"),
        ("stevens_n", profile.stevens_n, "stevens_n"),
        ("ifra_max_pct_edp", profile.ifra_max_pct_edp, "ifra_max_pct_edp"),
    )
    result: list[CapabilityEvidence] = []
    for field_name, value, provenance_key in fields:
        if value is None:
            continue
        source_ref = profile.provenance.get(provenance_key)
        result.append(
            CapabilityEvidence(
                field_name=field_name,
                value=value,
                source_ref=source_ref,
                evidence_grade=_evidence_grade(source_ref),
            )
        )
    return tuple(result)


def _stock_capability(record: InventoryMaterial) -> StockCapability:
    fraction = None
    if record.dilution > 0 and record.execution_hold_reason != "STOCK_FRACTION_UNSPECIFIED":
        fraction = Decimal(str(record.dilution))
    return StockCapability(
        raw_name=record.raw_name,
        status=record.status,
        active_fraction=fraction,
        fraction_basis=record.fraction_basis,
        carrier=record.carrier or None,
        execution_ready=record.execution_ready,
        hold_reason=record.execution_hold_reason or None,
    )


def _inventory_state(records: tuple[InventoryMaterial, ...]) -> InventoryCapabilityState:
    owned = tuple(
        record
        for record in records
        if record.status in {"owned", "owned_non_executable"}
    )
    if any(record.execution_ready for record in owned):
        return InventoryCapabilityState.OWNED_EXECUTABLE
    if owned:
        return InventoryCapabilityState.OWNED_HELD
    return InventoryCapabilityState.UNAVAILABLE


def _v5_indexes(
    materialized: CurrentInventoryMaterialization,
) -> tuple[dict[str, list[InventoryMaterial]], dict[str, list[Any]]]:
    stocks: dict[str, list[InventoryMaterial]] = {}
    requirements: dict[str, list[Any]] = {}
    for stock in materialized.stocks:
        for key in {stock.identity_name.casefold(), normalize_name(stock.identity_name)}:
            stocks.setdefault(key, []).append(stock)
    for requirement in materialized.requirements:
        for key in {
            requirement.identity_name.casefold(),
            normalize_name(requirement.identity_name),
        }:
            requirements.setdefault(key, []).append(requirement)
    return stocks, requirements


def _matched_v5(
    canonical_name: str,
    index: dict[str, list[Any]],
) -> tuple[Any, ...]:
    exact = index.get(canonical_name.casefold())
    if exact is not None:
        return tuple(exact)
    return tuple(index.get(normalize_name(canonical_name), ()))


def _conflicts(
    *,
    state: InventoryCapabilityState,
    current_stocks: tuple[StockCapability, ...],
    v5_stocks: tuple[InventoryMaterial, ...],
    profile: Material | None,
) -> tuple[CapabilityConflict, ...]:
    result: list[CapabilityConflict] = []
    current_owned = state in {
        InventoryCapabilityState.OWNED_EXECUTABLE,
        InventoryCapabilityState.OWNED_HELD,
    }
    if v5_stocks and not current_owned:
        result.append(
            CapabilityConflict(
                field="availability",
                prior_value="OWNED",
                effective_value=state.value,
                prior_source="V5_PLUS_USER_OVERLAY",
                effective_source="CURRENT_CONSOLIDATED_USER_STOCK_TEXT",
                resolution="LATEST_USER_STOCK_TEXT_CONTROLS_CURRENT_AVAILABILITY",
            )
        )
    if profile is not None:
        profile_stock = profile.user_stock_dilution
        profile_owned_conflict = bool(profile.user_in_inventory) != current_owned
        profile_stock_conflict = False
        if profile_stock not in (None, "") and current_owned:
            stock_text = " | ".join(item.raw_name.casefold() for item in current_stocks)
            profile_text = re.sub(r"\s+", " ", str(profile_stock).strip().casefold())
            profile_stock_conflict = profile_text not in stock_text
        if profile_owned_conflict or profile_stock_conflict:
            result.append(
                CapabilityConflict(
                    field="profile_stock",
                    prior_value=(
                        f"in_inventory={profile.user_in_inventory}; "
                        f"stock={profile.user_stock_dilution}"
                    ),
                    effective_value=" | ".join(item.raw_name for item in current_stocks),
                    prior_source="A_Z_MATERIAL_SPINE_LEGACY_STOCK_FIELDS",
                    effective_source="CURRENT_CONSOLIDATED_USER_STOCK_TEXT",
                    resolution="PROFILE_STOCK_FIELDS_IGNORED",
                )
            )
    return tuple(result)


def _blockers(
    *,
    state: InventoryCapabilityState,
    stocks: tuple[StockCapability, ...],
    profile: Material | None,
) -> tuple[str, ...]:
    blockers: list[str] = []
    if state is InventoryCapabilityState.UNAVAILABLE:
        blockers.append("MATERIAL_UNAVAILABLE")
    elif state is InventoryCapabilityState.OWNED_HELD:
        blockers.extend(
            item.hold_reason
            for item in stocks
            if item.status in {"owned", "owned_non_executable"} and item.hold_reason
        )
        if not blockers:
            blockers.append("QUANTITATIVE_STOCK_HOLD")
    if profile is None:
        blockers.append("MATERIAL_CAPABILITY_PROFILE_MISSING")
    return tuple(dict.fromkeys(blockers))


def build_material_capability_atlas(
    *,
    inventory_path: str | Path | None = None,
    material_data_dir: str | Path | None = None,
    require_pinned_authority: bool = True,
) -> MaterialCapabilityAtlas:
    """Reparse the complete current inventory and build one record per identity."""

    inventory_source = Path(inventory_path) if inventory_path else INVENTORY_PATH
    current_rows = tuple(
        parse_inventory(
            inventory_source,
            unique=False,
            include_solvents=True,
            include_unavailable=True,
        )
    )
    materialized = materialize_current_inventory(
        require_pinned_snapshot=require_pinned_authority,
        require_pinned_overlay=require_pinned_authority,
    )
    v5_stock_index, v5_requirement_index = _v5_indexes(materialized)

    data_dir = Path(material_data_dir) if material_data_dir else DEFAULT_DATA_DIR
    registry = load_registry(data_dir)
    normalized_profiles = _profile_lookup(registry.all())

    current_by_identity: dict[str, list[InventoryMaterial]] = {}
    for row in current_rows:
        current_by_identity.setdefault(row.name.casefold(), []).append(row)

    records: list[MaterialCapabilityRecord] = []
    for identity_key, raw_records in current_by_identity.items():
        inventory_records = tuple(raw_records)
        canonical_name = inventory_records[0].name
        current_stocks = tuple(_stock_capability(item) for item in inventory_records)
        state = _inventory_state(inventory_records)
        profile = _find_profile(
            canonical_name,
            registry=registry,
            normalized_profiles=normalized_profiles,
        )
        v5_stocks = _matched_v5(canonical_name, v5_stock_index)
        v5_requirements = _matched_v5(canonical_name, v5_requirement_index)
        evidence = _science_evidence(profile)
        if profile is None:
            knowledge_state = KnowledgeState.MISSING_PROFILE
        elif len(evidence) >= 5:
            knowledge_state = KnowledgeState.PROFILED
        else:
            knowledge_state = KnowledgeState.PARTIAL_PROFILE
        records.append(
            MaterialCapabilityRecord(
                canonical_name=canonical_name,
                identity_key=identity_key,
                categories=tuple(
                    dict.fromkeys(item.category for item in inventory_records if item.category)
                ),
                inventory_state=state,
                current_stocks=current_stocks,
                qualitative_selectable=state
                in {
                    InventoryCapabilityState.OWNED_EXECUTABLE,
                    InventoryCapabilityState.OWNED_HELD,
                },
                quantitative_execution_ready=state
                is InventoryCapabilityState.OWNED_EXECUTABLE,
                material_class=_material_class(canonical_name, profile),
                knowledge_state=knowledge_state,
                science_evidence=evidence,
                contextual_functions=(),
                temporal_registers=(),
                interfaces=(),
                takeover_modes=(),
                hedonic_claims=(),
                v5_source_rows=tuple(
                    sorted(
                        {
                            source_row
                            for item in v5_stocks
                            for source_row in item.source_rows
                        }
                        | {item.source_row for item in v5_requirements}
                    )
                ),
                v5_requirement_states=tuple(
                    dict.fromkeys(item.disposition for item in v5_requirements)
                ),
                conflicts=_conflicts(
                    state=state,
                    current_stocks=current_stocks,
                    v5_stocks=v5_stocks,
                    profile=profile,
                ),
                blockers=_blockers(
                    state=state,
                    stocks=current_stocks,
                    profile=profile,
                ),
                legacy_hedonic_value_ignored=(
                    profile is not None and profile.hedonic_valence is not None
                ),
            )
        )

    return MaterialCapabilityAtlas(
        records=records,
        current_stock_row_count=len(current_rows),
        v5_stock_count=len(materialized.stocks),
        v5_requirement_count=len(materialized.requirements),
        inventory_text_sha256=_normalized_sha256(inventory_source),
        v5_workbook_sha256=materialized.source_workbook_sha256,
        v5_snapshot_sha256=_normalized_sha256(CURRENT_INVENTORY_SNAPSHOT_PATH),
        user_overlay_sha256=_normalized_sha256(CURRENT_USER_INVENTORY_OVERLAY_PATH),
        material_data_fingerprint=_data_fingerprint(data_dir),
    )


__all__ = [
    "CapabilityConflict",
    "CapabilityEvidence",
    "EvidenceGrade",
    "InventoryCapabilityState",
    "KnowledgeState",
    "MaterialCapabilityAtlas",
    "MaterialCapabilityRecord",
    "MaterialClass",
    "StockCapability",
    "build_material_capability_atlas",
]
