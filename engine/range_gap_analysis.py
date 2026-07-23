"""Inventory-bound fragrance range and formula-corpus gap analysis.

This module keeps three questions separate:

1. Does the repository have a deterministic archetype contract?
2. Does the live inventory contain at least one identity for every required
   anchor group in that contract?
3. Is there a formula file that explicitly declares the archetype?

None of those facts proves that a physical batch was made, smells correct, is
safe, or passes the release pipeline.  The separation prevents the old static
"20 of 22 families are fully buildable" prose from becoming release authority.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path

from engine.families.registry import ARCHETYPES, ArchetypeSpec, GroupRule
from engine.ingredient_intelligence import get_profile
from engine.inventory_parser import InventoryMaterial, parse_inventory
from engine.knowledge.perfume_taxonomy import (
    FAMILY_SUBFAMILY_MAP,
    SUBFAMILY_DESCRIPTIONS,
    PerfumeSubfamily,
)
from engine.name_utils import normalize_name

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INVENTORY = PROJECT_ROOT / "inventory.txt"
DEFAULT_FORMULAS = PROJECT_ROOT / "formulas"

BUILDABILITY_AUTHORITY = "LIVE_INVENTORY_IDENTITY_AND_REGISTERED_ANCHOR_CONTRACT"
FORMULA_AUTHORITY = "REPOSITORY_EXPLICIT_ARCHETYPE_DECLARATION_ONLY"
TAXONOMY_AUTHORITY = "REGISTERED_CONTRACT_COVERAGE_ONLY"


# Only unambiguous mappings are declared. An iris-amber or Layton-DNA contract
# is still reported in registered_archetypes, but is not forced into an Edwards-
# style taxonomy bucket merely to improve coverage numbers.
SUBFAMILY_CONTRACTS: dict[str, tuple[str, ...]] = {
    "citrus_classical": ("citrus_classical.4711_reference",),
    "citrus_aromatic": ("citrus_aromatic.eau_sauvage_reference",),
    "fougere_classical": ("fougere_classical.fougere_royale_reference",),
    "fougere_aromatic": (
        "aromatic_fougere.classic_reference",
        "aromatic_fougere.azzaro_reference",
    ),
    "fougere_modern_mineral": ("aromatic_fougere.modern_mineral",),
    "fougere_modern_tonka": ("aromatic_fougere.modern_tonka_mass",),
    "floral_soliflore": ("floral_soliflore.rose_reference",),
    "floral_white": ("floral_white.fracas_reference",),
    "floral_muguet": ("floral_muguet.diorissimo_reference",),
    "floral_aldehydic": ("floral_aldehydic.no5_reference",),
    "floral_green": ("floral_green.no19_reference",),
    "floral_powdery": ("floral_powdery.apres_londee_reference",),
    "chypre_classical": ("chypre_classical.coty_reference",),
    "chypre_floral": ("chypre_floral.miss_dior_reference",),
    "chypre_fruity": ("chypre_fruity.mitsouko_reference",),
    "chypre_green": ("chypre_green.vent_vert_reference",),
    "chypre_leathery": ("chypre_leathery.bandit_reference",),
    "oriental_classical": ("oriental_classical.shalimar_reference",),
    "oriental_floral": ("oriental_floral.lheure_bleue_reference",),
    "woody_classical": ("woody.vetiver_classical",),
}


@dataclass(frozen=True, slots=True)
class AnchorAvailability:
    name: str
    status: str
    basis: str
    minimum_percent: float | None
    available_stock: tuple[str, ...]
    unavailable_stock: tuple[str, ...]
    contract_options: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ArchetypeCoverage:
    key: str
    family: str
    label: str
    role: str
    buildability_status: str
    formula_record_status: str
    anchors: tuple[AnchorAvailability, ...]
    missing_anchor_groups: tuple[str, ...]
    formula_files: tuple[str, ...]
    buildability_authority: str = BUILDABILITY_AUTHORITY
    formula_authority: str = FORMULA_AUTHORITY


@dataclass(frozen=True, slots=True)
class TaxonomyCoverage:
    root_family: str
    subfamily: str
    status: str
    contract_archetypes: tuple[str, ...]
    formula_record_status: str
    description: str
    authority: str = TAXONOMY_AUTHORITY


@dataclass(frozen=True, slots=True)
class RangeCoverageReport:
    inventory_available_count: int
    formula_files_scanned: int
    explicit_declaration_count: int
    registered_archetypes: tuple[ArchetypeCoverage, ...]
    taxonomy: tuple[TaxonomyCoverage, ...]
    buildable_without_formula_record: tuple[str, ...]
    unregistered_formula_declarations: tuple[str, ...]
    limitations: tuple[str, ...] = (
        "Inventory presence does not establish remaining stock quantity.",
        "Anchor availability does not establish formula quality, OAV balance, IFRA compliance, or release-gate success.",
        "A repository formula declaration does not prove that a physical batch was compounded.",
        "An unmodeled taxonomy subfamily is UNKNOWN, not unbuildable.",
        "Reference examples in taxonomy prose are descriptive and are not formula-ratio evidence.",
    )

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _identity_key(name: str) -> str:
    profile = get_profile(name)
    return normalize_name(profile.name if profile is not None else name)


def _stock_index(
    records: list[InventoryMaterial],
) -> dict[str, tuple[InventoryMaterial, ...]]:
    grouped: dict[str, list[InventoryMaterial]] = {}
    for record in records:
        key = _identity_key(record.identity_name or record.name)
        grouped.setdefault(key, []).append(record)
    return {key: tuple(values) for key, values in grouped.items()}


def _scan_formula_declarations(
    formulas_dir: Path,
) -> tuple[dict[str, tuple[str, ...]], int, int]:
    declarations: dict[str, set[str]] = {}
    files = sorted(formulas_dir.rglob("*.md")) if formulas_dir.exists() else []
    pattern = re.compile(
        r"^\s*\*\*Family archetype:\*\*\s*`?([^`\r\n]+?)`?\s*$",
        flags=re.IGNORECASE,
    )
    declaration_count = 0
    for path in files:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        for line in lines:
            match = pattern.match(line)
            if match is None:
                continue
            key = match.group(1).strip().strip("`*_ ")
            if not key:
                continue
            declaration_count += 1
            relative = path.relative_to(formulas_dir).as_posix()
            declarations.setdefault(key, set()).add(relative)
    frozen = {key: tuple(sorted(paths)) for key, paths in declarations.items()}
    return frozen, len(files), declaration_count


def _anchor_availability(
    rule: GroupRule,
    available_index: dict[str, tuple[InventoryMaterial, ...]],
    all_index: dict[str, tuple[InventoryMaterial, ...]],
) -> AnchorAvailability:
    option_keys = {_identity_key(name) for name in rule.materials}
    available = sorted(
        {
            record.name
            for key in option_keys
            for record in available_index.get(key, ())
            if record.status == "owned"
        }
    )
    unavailable = sorted(
        {
            record.name
            for key in option_keys
            for record in all_index.get(key, ())
            if record.status != "owned"
        }
    )
    required = rule.minimum is not None and rule.minimum > 0
    status = (
        "AVAILABLE"
        if available
        else "MISSING_REQUIRED"
        if required
        else "OPTIONAL_UNAVAILABLE"
    )
    return AnchorAvailability(
        name=rule.name,
        status=status,
        basis=rule.basis,
        minimum_percent=rule.minimum,
        available_stock=tuple(available),
        unavailable_stock=tuple(unavailable),
        contract_options=tuple(rule.materials),
    )


def _evaluate_archetype(
    spec: ArchetypeSpec,
    available_index: dict[str, tuple[InventoryMaterial, ...]],
    all_index: dict[str, tuple[InventoryMaterial, ...]],
    declarations: dict[str, tuple[str, ...]],
) -> ArchetypeCoverage:
    anchors = tuple(
        _anchor_availability(rule, available_index, all_index)
        for rule in spec.anchors
    )
    missing = tuple(
        anchor.name for anchor in anchors if anchor.status == "MISSING_REQUIRED"
    )
    formula_files = declarations.get(spec.key, ())
    return ArchetypeCoverage(
        key=spec.key,
        family=spec.family,
        label=spec.label,
        role=spec.role,
        buildability_status=(
            "BUILDABLE_FROM_AVAILABLE_STOCK_IDENTITIES"
            if not missing
            else "PARTIAL_MISSING_ANCHOR_GROUPS"
        ),
        formula_record_status=(
            "DECLARED_FORMULA_PRESENT"
            if formula_files
            else "NO_DECLARED_FORMULA_RECORD"
        ),
        anchors=anchors,
        missing_anchor_groups=missing,
        formula_files=formula_files,
    )


def analyze_range_coverage(
    inventory_path: str | Path = DEFAULT_INVENTORY,
    formulas_dir: str | Path = DEFAULT_FORMULAS,
) -> RangeCoverageReport:
    inventory = Path(inventory_path)
    formulas = Path(formulas_dir)
    available = parse_inventory(
        inventory,
        unique=True,
        include_solvents=False,
        include_unavailable=False,
    )
    all_records = parse_inventory(
        inventory,
        unique=False,
        include_solvents=True,
        include_unavailable=True,
    )
    declarations, files_scanned, declaration_count = _scan_formula_declarations(
        formulas
    )
    available_index = _stock_index(available)
    all_index = _stock_index(all_records)

    archetypes = tuple(
        _evaluate_archetype(
            spec,
            available_index,
            all_index,
            declarations,
        )
        for spec in sorted(ARCHETYPES.values(), key=lambda value: value.key)
    )
    by_key = {coverage.key: coverage for coverage in archetypes}

    root_by_subfamily = {
        subfamily.value: root.value
        for root, subfamilies in FAMILY_SUBFAMILY_MAP.items()
        for subfamily in subfamilies
    }
    taxonomy_rows: list[TaxonomyCoverage] = []
    for subfamily in sorted(PerfumeSubfamily, key=lambda value: value.value):
        contracts = SUBFAMILY_CONTRACTS.get(subfamily.value, ())
        contracted = tuple(by_key[key] for key in contracts if key in by_key)
        if not contracted:
            status = "UNMODELED_NO_BUILDABILITY_CLAIM"
        elif any(
            row.buildability_status == "BUILDABLE_FROM_AVAILABLE_STOCK_IDENTITIES"
            for row in contracted
        ):
            status = "CONTRACTED_BUILDABLE_FROM_AVAILABLE_STOCK_IDENTITIES"
        else:
            status = "CONTRACTED_PARTIAL_MISSING_ANCHORS"
        taxonomy_rows.append(
            TaxonomyCoverage(
                root_family=root_by_subfamily[subfamily.value],
                subfamily=subfamily.value,
                status=status,
                contract_archetypes=contracts,
                formula_record_status=(
                    "DECLARED_FORMULA_PRESENT"
                    if any(row.formula_files for row in contracted)
                    else "NO_DECLARED_FORMULA_RECORD"
                    if contracted
                    else "UNMODELED_FORMULA_MAPPING"
                ),
                description=SUBFAMILY_DESCRIPTIONS[subfamily],
            )
        )

    buildable_unmade = tuple(
        row.key
        for row in archetypes
        if row.buildability_status == "BUILDABLE_FROM_AVAILABLE_STOCK_IDENTITIES"
        and row.formula_record_status == "NO_DECLARED_FORMULA_RECORD"
    )
    unregistered = tuple(sorted(set(declarations) - set(ARCHETYPES)))
    return RangeCoverageReport(
        inventory_available_count=len(available),
        formula_files_scanned=files_scanned,
        explicit_declaration_count=declaration_count,
        registered_archetypes=archetypes,
        taxonomy=tuple(taxonomy_rows),
        buildable_without_formula_record=buildable_unmade,
        unregistered_formula_declarations=unregistered,
    )


def format_range_coverage(report: RangeCoverageReport) -> str:
    """Render a compact, authority-labelled Markdown report."""

    buildable = sum(
        row.buildability_status == "BUILDABLE_FROM_AVAILABLE_STOCK_IDENTITIES"
        for row in report.registered_archetypes
    )
    contracted_taxonomy = sum(
        row.status != "UNMODELED_NO_BUILDABILITY_CLAIM" for row in report.taxonomy
    )
    lines = [
        "# Live Fragrance Range Coverage",
        "",
        f"- Available fragrance stock identities: {report.inventory_available_count}",
        f"- Registered archetypes buildable by anchor identity: {buildable}/{len(report.registered_archetypes)}",
        f"- Taxonomy subfamilies with deterministic contracts: {contracted_taxonomy}/{len(report.taxonomy)}",
        f"- Formula files scanned: {report.formula_files_scanned}",
        f"- Explicit archetype declarations: {report.explicit_declaration_count}",
        "",
        "## Buildable registered archetypes with no declared formula record",
        "",
    ]
    if report.buildable_without_formula_record:
        lines.extend(f"- `{key}`" for key in report.buildable_without_formula_record)
    else:
        lines.append("- None")
    lines.extend(["", "## Unregistered formula declarations", ""])
    if report.unregistered_formula_declarations:
        lines.extend(f"- `{key}`" for key in report.unregistered_formula_declarations)
    else:
        lines.append("- None")
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {limitation}" for limitation in report.limitations)
    return "\n".join(lines)


__all__ = [
    "AnchorAvailability",
    "ArchetypeCoverage",
    "RangeCoverageReport",
    "SUBFAMILY_CONTRACTS",
    "TaxonomyCoverage",
    "analyze_range_coverage",
    "format_range_coverage",
]
