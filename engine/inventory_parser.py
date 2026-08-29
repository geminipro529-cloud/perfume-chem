"""Shared inventory parsing utilities.

Normalizes `inventory.txt` into consistent material records so the pipeline
does not maintain conflicting parsers and counts across modules. Duplicate
canonical materials are collapsed conservatively by keeping the highest
available dilution entry.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INVENTORY_PATH = PROJECT_ROOT / "inventory.txt"

_HEADING_RE = re.compile(r"^---\s+(.+?)\s+---$")
_BULLET_RE = re.compile(r"^[-•]\s+(.+?)\s*$")
_PERCENT_RE = re.compile(r"\(\s*~?\s*(\d+(?:\.\d+)?)\s*%(?:[^)]*)\)")

_SOLVENT_CATEGORY_TOKENS = ("solvent", "carrier")
_SOLVENT_MATERIALS = {
    "ethanol 96%",
    "dipropylene glycol",
    "dpg",
    "isopropyl myristate",
    "ipm",
    "triethyl citrate",
    "tec",
    "diethyl phthalate",
    "dep",
}


@dataclass(frozen=True)
class InventoryMaterial:
    name: str
    dilution: float
    category: str
    raw_name: str
    status: str
    fraction_basis: str = "unspecified"
    carrier: str = ""
    approximate: bool = False
    identity_name: str = ""


@dataclass(frozen=True)
class StockSpecification:
    """One declared stock fraction without pretending unlike bases are equivalent."""

    fraction: float
    fraction_basis: str
    carrier: str
    approximate: bool
    declared: bool
    raw: str

    def as_dict(self) -> dict[str, object]:
        return {
            "fraction": self.fraction,
            "fraction_basis": self.fraction_basis,
            "carrier": self.carrier,
            "approximate": self.approximate,
            "declared": self.declared,
            "raw": self.raw,
        }


def _parse_dilution(raw_name: str) -> float:
    match = _PERCENT_RE.search(raw_name)
    if not match:
        return 1.0
    return float(match.group(1)) / 100.0


def _normalize_carrier(value: str) -> str:
    value = re.sub(r"\b\d+\s*:\s*\d+\b", "", value)
    value = re.sub(r"\s+", " ", value.strip(" .,:;)-").lower())
    return value


def parse_stock_specification(
    raw: str,
    *,
    assume_neat_when_missing: bool = False,
) -> StockSpecification:
    """Parse fraction, physical basis, and carrier from inventory/formula text.

    A bare inventory entry means neat by repository convention.  A blank or dash
    in a formula does not: callers can therefore distinguish an explicit neat
    declaration from missing stock metadata.
    """

    text = str(raw or "").strip().replace("**", "").replace("`", "")
    low = text.lower()
    missing_tokens = {"", "-", "--", "---", "—", "–", "na", "n/a"}
    explicit_neat = low in {"neat", "pure", "undiluted"}
    match = re.search(r"~?\s*(\d+(?:[.,]\d+)?)\s*%", text)

    if explicit_neat or (match is None and assume_neat_when_missing):
        fraction = 1.0
        basis = "neat"
        declared = True
    elif match is not None:
        fraction = float(match.group(1).replace(",", ".")) / 100.0
        if re.search(r"\bw\s*/\s*w\b", low):
            basis = "mass_fraction"
        elif re.search(r"\bw\s*/\s*v\b", low):
            basis = "mass_per_volume"
        elif re.search(r"\bv\s*/\s*v\b", low):
            basis = "volume_fraction"
        else:
            basis = "unspecified"
        declared = True
    else:
        fraction = 1.0
        basis = "unspecified"
        declared = low not in missing_tokens

    carrier_match = re.search(r"\bin\s+([^),;#—–]+)", text, flags=re.IGNORECASE)
    carrier = _normalize_carrier(carrier_match.group(1)) if carrier_match else ""
    # A preparation statement such as "30% w/v, 3 g in 10 mL" declares a
    # concentration denominator, not the identity of a solvent. Treating
    # "10 mL" as a carrier silently fabricates finished-matrix provenance.
    if re.fullmatch(
        r"\d+(?:[.,]\d+)?\s*(?:ml|ul|µl|μl|l)",
        carrier,
        flags=re.IGNORECASE,
    ):
        carrier = ""
    approximate = bool("~" in text or re.search(r"\b(?:approx|approximately)\b", low))
    return StockSpecification(
        fraction=fraction,
        fraction_basis=basis,
        carrier=carrier,
        approximate=approximate,
        declared=declared,
        raw=text,
    )


def _parse_status(raw_name: str) -> str:
    upper = raw_name.upper()
    if re.search(r"\bHOLD\b", upper):
        return "hold"
    if "DEPLETED" in upper:
        return "depleted"
    if "OUT OF STOCK" in upper:
        return "out_of_stock"
    if "RAN OUT" in upper:
        return "ran_out"
    if "DON'T HAVE" in upper or "DONT HAVE" in upper:
        return "not_owned"
    return "owned"


def _strip_status(raw_name: str) -> str:
    return re.sub(r"\s*\[[^\]]+\]\s*$", "", raw_name).strip()


def _canonical_name(raw_name: str) -> str:
    clean = _strip_status(raw_name)
    # Remove trailing `# comment` before stripping parenthetical
    clean = re.sub(r"\s*#.*$", "", clean).strip()
    return re.sub(r"\s*\([^)]*\)\s*$", "", clean).strip()


def _identity_name(raw_name: str) -> str:
    """Remove stock preparation text while preserving identity-bearing variants."""

    clean = _strip_status(raw_name)
    clean = re.sub(r"\s*#.*$", "", clean).strip()
    parenthetical = re.search(r"\s*\(([^)]*)\)\s*$", clean)
    if not parenthetical:
        return clean
    content = parenthetical.group(1).lower()
    stock_tokens = ("%", "w/w", "w/v", "v/v", "neat", "dilut", " in dpg", " in dep", " in tec", " in ipm")
    if any(token in content for token in stock_tokens):
        return clean[: parenthetical.start()].strip()
    return clean


def _is_solvent(record: InventoryMaterial) -> bool:
    category = record.category.lower()
    if any(token in category for token in _SOLVENT_CATEGORY_TOKENS):
        return True
    return record.name.lower() in _SOLVENT_MATERIALS


def parse_inventory(
    path: Path | None = None,
    *,
    unique: bool = True,
    include_solvents: bool = True,
    include_unavailable: bool = True,
) -> list[InventoryMaterial]:
    """Parse inventory.txt into normalized material records.

    When `unique=True`, duplicate canonical materials are collapsed by keeping
    the highest-available dilution entry.
    """
    path = path or INVENTORY_PATH
    if not path.exists():
        return []

    materials: list[InventoryMaterial] = []
    current_category = ""

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue

        heading_match = _HEADING_RE.match(line)
        if heading_match:
            current_category = heading_match.group(1).strip().lower()
            continue

        bullet_match = _BULLET_RE.match(line)
        if not bullet_match:
            continue

        raw_name = bullet_match.group(1).strip()
        stock_source = re.sub(r"\s*#.*$", "", raw_name).strip()
        stock = parse_stock_specification(
            stock_source,
            assume_neat_when_missing=True,
        )
        record = InventoryMaterial(
            name=_canonical_name(raw_name),
            dilution=stock.fraction,
            category=current_category,
            raw_name=raw_name,
            status=_parse_status(raw_name),
            fraction_basis=stock.fraction_basis,
            carrier=stock.carrier,
            approximate=stock.approximate,
            identity_name=_identity_name(raw_name),
        )
        if not include_unavailable and record.status != "owned":
            continue
        if not include_solvents and _is_solvent(record):
            continue
        materials.append(record)

    if not unique:
        return materials

    deduped: dict[str, InventoryMaterial] = {}
    for record in materials:
        key = record.name.lower()
        existing = deduped.get(key)
        if existing is None or record.dilution > existing.dilution:
            deduped[key] = record

    return list(deduped.values())


def inventory_names(
    path: Path | None = None,
    *,
    unique: bool = True,
    include_solvents: bool = True,
    include_unavailable: bool = True,
) -> list[str]:
    return [
        record.name
        for record in parse_inventory(
            path,
            unique=unique,
            include_solvents=include_solvents,
            include_unavailable=include_unavailable,
        )
    ]


def inventory_counts(path: Path | None = None) -> dict[str, int]:
    """Return raw and normalized inventory counts for reporting."""
    path = path or INVENTORY_PATH
    raw = parse_inventory(path, unique=False, include_solvents=True)
    unique_all = parse_inventory(path, unique=True, include_solvents=True)
    unique_fragrance = parse_inventory(path, unique=True, include_solvents=False)
    return {
        "raw_entries": len(raw),
        "unique_normalized": len(unique_all),
        "unique_fragrance": len(unique_fragrance),
        "solvent_or_carrier": len(unique_all) - len(unique_fragrance),
        "duplicate_canonical_entries": len(raw) - len(unique_all),
    }
