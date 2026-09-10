"""Parse formula metadata block from markdown formula files.

Format (Prada_LHomme_Architecture_Control template):
  **Date:** YYYY-MM-DD
  **Claim mode:** named_reference | unclaimed
  **Reference contract:** <contract_id> | none
  **Reference scope:** architecture | quantitative_similarity | sensory_similarity
  **Family archetype:** <key>
  **Reference evidence:** <one-sentence>
  **Official source:** <URL>
  **Concentration:** <uL concentrate> + <uL ethanol>; <final volume>; <% v/v>
  **Status:** Research control | Pending bench | Released

Also provides pipeline_preflight_guard() — hard blocks + warns before gate runs.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path


def _normalize_fallback(name: str) -> str:
    return name.lower().strip()


def _suggest_fallback(name: str, inventory_names: set[str]) -> str:
    return "no replacement found"


@dataclass
class FormulaMetadata:
    date: str = ""
    claim_mode: str = ""  # "named_reference" or "unclaimed"
    reference_contract: str = ""  # contract_id or "none"
    reference_scope: str = ""  # "architecture" / "quantitative_similarity" / "sensory_similarity"
    family_archetype: str = ""  # key from ARCHETYPES
    reference_evidence: str = ""
    official_source: str = ""
    concentration: str = ""  # raw text
    status: str = ""  # "Research control" | "Pending bench" | "Released"
    raw_lines: list[str] = field(default_factory=list)

    def has_metadata(self) -> bool:
        return bool(self.claim_mode)

    def is_claimed(self) -> bool:
        return self.claim_mode == "named_reference"

    def is_quantitative(self) -> bool:
        return self.reference_scope == "quantitative_similarity"

    def is_unclaimed(self) -> bool:
        return self.claim_mode in ("unclaimed", "none", "")


_METADATA_FIELD_PATTERNS: list[tuple[str, str]] = [
    ("date", r"\*\*Date:\*\*\s*(.+)"),
    ("claim_mode", r"\*\*Claim mode:\*\*\s*(.+)"),
    ("reference_contract", r"\*\*Reference contract:\*\*\s*(.+)"),
    ("reference_scope", r"\*\*Reference scope:\*\*\s*(.+)"),
    ("family_archetype", r"\*\*Family archetype:\*\*\s*(.+)"),
    ("reference_evidence", r"\*\*Reference evidence:\*\*\s*(.+)"),
    ("official_source", r"\*\*Official source:\*\*\s*(.+)"),
    ("concentration", r"\*\*Concentration:\*\*\s*(.+)"),
    ("status", r"\*\*Status:\*\*\s*(.+)"),
]


def parse_formula_metadata(formula_path: str) -> FormulaMetadata:
    """Extract metadata block from a formula markdown file."""
    meta = FormulaMetadata()
    try:
        with open(formula_path, encoding="utf-8") as fh:
            lines = fh.readlines()
    except (FileNotFoundError, OSError):
        return meta

    header_lines: list[str] = []
    for line in lines:
        if line.startswith("## Concept Lock") or line.startswith("## Formula"):
            break
        header_lines.append(line)

    text = "".join(header_lines)

    for field_name, pattern in _METADATA_FIELD_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            setattr(meta, field_name, m.group(1).strip())

    meta.raw_lines = header_lines

    if not meta.claim_mode and not meta.date:
        for line in header_lines:
            stripped = line.strip()
            if stripped.startswith("**Reference claim:"):
                claim = stripped.split(":", 1)[-1].strip().rstrip("*").strip()
                if claim.lower() == "none":
                    meta.claim_mode = "unclaimed"
                    break

    return meta


# ── Pipeline Preflight Guard ───────────────────────────────────────────

from dataclasses import dataclass as _dc  # noqa: E402  # sys.path
from dataclasses import field as _field  # noqa: E402  # sys.path


@_dc
class PreflightResult:
    hard_blocks: list[str] = _field(default_factory=list)
    warnings: list[str] = _field(default_factory=list)
    metadata: FormulaMetadata | None = None

    def ok(self) -> bool:
        return len(self.hard_blocks) == 0

    def to_dict(self) -> dict:
        return {
            "hard_blocks": self.hard_blocks,
            "warnings": self.warnings,
            "passed": self.ok(),
        }


def _extract_material_names(formula_path: str) -> list[str]:
    """Extract material names only from dose-bearing formula tables.

    Narrative tables such as accord architecture and selection rationale are
    not formula authority.  A usable table must identify both an ingredient
    column and a numeric dose/percentage column.
    """
    names: list[str] = []
    try:
        with open(formula_path, encoding="utf-8") as fh:
            text = fh.read()
    except (FileNotFoundError, OSError):
        return names

    text = text.split("<!-- PIPELINE_ANALYSIS_START -->", 1)[0]

    def cells(line: str) -> list[str]:
        values = [cell.strip().replace("**", "").replace("`", "") for cell in line.split("|")]
        if values and not values[0]:
            values = values[1:]
        if values and not values[-1]:
            values = values[:-1]
        return values

    def normalized(value: str) -> str:
        value = value.replace("ยต", "u").replace("ฮผ", "u")
        return re.sub(r"\s+", " ", value.casefold()).strip()

    def separator(line: str) -> bool:
        return bool(re.fullmatch(r"\|[\s:\-|]+\|?", line.strip()))

    lines = text.splitlines()
    table_columns: tuple[int, int] | None = None
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("|"):
            table_columns = None
            continue
        if index + 1 < len(lines) and separator(lines[index + 1]):
            headers = [normalized(value) for value in cells(stripped)]
            name_index = next(
                (
                    position
                    for position, header in enumerate(headers)
                    if any(token in header for token in ("ingredient", "material", "component"))
                ),
                None,
            )
            dose_index = next(
                (
                    position
                    for position, header in enumerate(headers)
                    if (
                        ("amount" in header and any(unit in header for unit in ("ul", "ml", " g")))
                        or header in {"%", "percent", "percentage"}
                    )
                ),
                None,
            )
            table_columns = (
                (name_index, dose_index)
                if name_index is not None and dose_index is not None
                else None
            )
            continue
        if separator(stripped) or table_columns is None:
            continue

        row = cells(stripped)
        name_index, dose_index = table_columns
        if max(name_index, dose_index) >= len(row):
            continue
        dose_match = re.search(r"[-+]?\d[\d,\s]*(?:\.\d+)?", row[dose_index])
        if dose_match is None:
            continue
        dose = float(dose_match.group(0).replace(",", "").replace(" ", ""))
        if dose <= 0:
            continue

        name = row[name_index].strip()
        for part in (piece.strip() for piece in name.split(" + ")):
            low = part.casefold()
            if (
                not part
                or part.startswith("---")
                or re.fullmatch(r"[\d.,\s]+", part)
                or "total" in low
                or "ethanol" in low
                or "finished bottle" in low
            ):
                continue
            names.append(part)
    return names


def _load_inventory_names(inventory_path: str = "inventory.txt") -> set[str]:
    """Load material identities from the authoritative current inventory.

    The default release path must use the pinned inventory materialization,
    because parsing the prose form of ``inventory.txt`` loses successor-overlay
    identities and stock corrections.  Explicit alternate inventory files keep
    the lightweight text behavior for isolated tests and legacy callers.
    """
    requested_path = Path(inventory_path).resolve()
    default_path = Path("inventory.txt").resolve()
    if requested_path == default_path:
        from engine.inventory_parser import materialize_current_inventory

        materialized = materialize_current_inventory()
        return {
            name
            for stock in materialized.stocks
            for name in (stock.name, stock.identity_name)
            if name
        }

    names: set[str] = set()
    try:
        with requested_path.open(encoding="utf-8") as fh:
            for line in fh:
                stripped = line.strip()
                if stripped.startswith("- "):
                    material = stripped[2:].strip()
                    material = re.sub(r"\s*#.*$", "", material).strip()
                    material = re.sub(r"\s*\(\d+%[^)]*\)", "", material).strip()
                    names.add(material)
    except FileNotFoundError:
        pass
    return names


def pipeline_preflight_guard(
    formula_path: str,
    brief: str | None = None,
    inventory_path: str = "inventory.txt",
) -> PreflightResult:
    """Run all preflight checks before a gate run. Returns HARD_BLOCKs and WARNs."""
    result = PreflightResult()

    # Block 1: Metadata required
    meta = parse_formula_metadata(formula_path)
    result.metadata = meta
    if not meta.has_metadata() and not meta.is_unclaimed():
        result.hard_blocks.append(
            "MISSING_METADATA: Formula has no metadata block. "
            "Add explicit metadata or set `**Reference claim:** none`."
        )

    # Block 2: Inventory stock contract
    formula_materials = _extract_material_names(formula_path)
    inventory_names = _load_inventory_names(inventory_path)
    _normalize: Callable[[str], str]
    try:
        from engine.name_utils import normalize_name as _normalize
    except ImportError:
        _normalize = _normalize_fallback

    normalized_inventory_names = {
        normalized
        for name in inventory_names
        if (normalized := _normalize(name))
    }
    missing = []
    for fm in formula_materials:
        fm_resolved = _normalize(fm)
        if fm_resolved and fm_resolved not in normalized_inventory_names:
            missing.append(fm)
    if missing:
        # Suggest replacements from inventory for each missing material
        suggestions = []
        _suggest: Callable[[str, set[str]], str]
        try:
            from engine.ingredient_intelligence import suggest_replacement as _suggest
        except ImportError:
            _suggest = _suggest_fallback

        for m in missing[:5]:
            alt = _suggest(m, inventory_names) if callable(_suggest) else "check inventory"
            suggestions.append(f"{m} → try {alt}")
        result.warnings.append(
            f"INVENTORY_MISSING: {len(missing)} materials not in inventory. "
            + f"Replacements: {'; '.join(suggestions)}"
            + ("..." if len(missing) > 5 else "")
        )

    # Block 3: Quantitative authority
    if meta.is_claimed() and meta.is_quantitative():
        result.hard_blocks.append(
            "QUANTITATIVE_AUTHORITY: quantitative_similarity claims require "
            "density chain for ppm w/w — verify density data before proceeding."
        )

    # Block 4: Chemical family compatibility (F11)
    try:
        from engine.ingredient_intelligence import check_natural_compatibility

        natural_names = [
            n
            for n in formula_materials
            if any(tag in n.lower() for tag in ("eo", "absolute", "resinoid", "concrete", "co2"))
        ]
        if len(natural_names) >= 2:
            incompat = check_natural_compatibility(natural_names)
            if incompat:
                result.warnings.extend(incompat)
    except ImportError:
        pass

    # Block 5: Thai retail bracket cost (placeholder)
    result.warnings.append(
        "COST_TICKER: Material cost estimate not yet available — "
        "check data/thai_market_sales_2500_15000_thb.md manually."
    )

    # Block 6: EU 2023/1545 82-allergen (WARN only per user)
    result.warnings.append(
        "EU_1545_WARN: EU 2023/1545 82-allergen check deferred to "
        "verify_formula_protocol pipeline gate. Review before release."
    )

    return result
