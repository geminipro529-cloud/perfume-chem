"""Versioned, fail-closed loaders for immutable perfume design snapshots.

The loaders in this module translate source artifacts into the same
``FormulaSnapshotV1`` contract.  They do not bind inventory, infer stock lots,
or convert a solid mass into a liquid volume.  Formula-specific compatibility
logic is confined to the two explicitly versioned manifest adapters; the
Markdown table normalizer is generic.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable, Mapping

from .contracts import FormulaComponentV1, FormulaSnapshotV1, decimal_text

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_R5_MANIFEST = (
    ROOT
    / "data"
    / "governance"
    / "lavande_ambre_profond_r5_design_comparator_20260923.json"
)
DEFAULT_R6_MANIFEST = (
    ROOT
    / "data"
    / "governance"
    / "lavande_ambre_profond_r6_aimi_design_successor_20260926.json"
)
DEFAULT_PARALLEL_A_FORMULA = (
    ROOT / "formulas" / "Lavande_Ambre_Profond_Parallel_A_30mL_EDP.md"
)


class SnapshotSourceError(ValueError):
    """Raised when a source artifact cannot prove its declared snapshot."""


@dataclass(frozen=True, slots=True)
class FormulaSnapshotLoadV1:
    """A source-bound design snapshot with physically separate totals."""

    snapshot: FormulaSnapshotV1
    source_path: str
    source_sha256: str
    source_schema_version: str
    canonical_rows_sha256: str
    liquid_total_ul_decimal: str
    solid_total_mg_decimal: str
    validation_state: str
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in ("source_sha256", "canonical_rows_sha256"):
            value = getattr(self, name)
            if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
                raise ValueError(f"{name} must be a lowercase SHA-256")
        object.__setattr__(
            self,
            "liquid_total_ul_decimal",
            decimal_text(self.liquid_total_ul_decimal, "liquid_total_ul_decimal", nonnegative=True),
        )
        object.__setattr__(
            self,
            "solid_total_mg_decimal",
            decimal_text(self.solid_total_mg_decimal, "solid_total_mg_decimal", nonnegative=True),
        )


def _file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _canonical_hash(value: object) -> str:
    return sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()


def _load_json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SnapshotSourceError(f"could not read snapshot source {path}") from exc
    if not isinstance(value, dict):
        raise SnapshotSourceError("snapshot manifest must contain a JSON object")
    return value


def _decimal(value: object, name: str) -> Decimal:
    if isinstance(value, bool):
        raise SnapshotSourceError(f"{name} cannot be boolean")
    try:
        parsed = Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, AttributeError, ValueError) as exc:
        raise SnapshotSourceError(f"{name} must be a finite decimal") from exc
    if not parsed.is_finite() or parsed <= 0:
        raise SnapshotSourceError(f"{name} must be a positive finite decimal")
    return parsed


def _unit(value: object) -> str:
    normalized = str(value).strip().replace("µ", "u").replace("μ", "u")
    if normalized not in {"uL", "mL", "mg", "g"}:
        raise SnapshotSourceError(f"unsupported physical unit: {value!r}")
    return normalized


def _product_id(label: str) -> str:
    """Return an opaque unbound identity; exact source text remains attached."""

    digest = sha256(label.encode("utf-8")).hexdigest()[:24]
    return f"unbound-design-product:{digest}"


def _manifest_row_component(row: Mapping[str, Any]) -> FormulaComponentV1:
    try:
        source_row = row["source_row"]
        basket = str(row["basket"]).strip()
        label = str(row["material"]).strip()
        stock = str(row["required_stock"]).strip()
        evidence = str(row["evidence"]).strip()
        amount = _decimal(row["dose"], "dose")
        unit = _unit(row["unit"])
    except KeyError as exc:
        raise SnapshotSourceError(f"manifest row missing {exc.args[0]}") from exc
    if isinstance(source_row, bool) or not isinstance(source_row, int) or source_row < 1:
        raise SnapshotSourceError("source_row must be a positive integer")
    if not all((basket, label, stock, evidence)):
        raise SnapshotSourceError("manifest row text fields cannot be empty")
    return FormulaComponentV1(
        row_id=f"source-row-{source_row}",
        product_id=_product_id(label),
        stock_id=None,
        amount_decimal=decimal_text(amount, "dose", positive=True),
        amount_unit=unit,  # type: ignore[arg-type]
        basket=basket,
        operation="MASS_ADD" if unit in {"mg", "g"} else "DIRECT_ADD",
        source_row=source_row,
        source_material_label=label,
        required_stock_description=stock,
        source_evidence_id=evidence,
    )


def _totals(components: Iterable[FormulaComponentV1]) -> tuple[str, str]:
    liquid_ul = Decimal("0")
    solid_mg = Decimal("0")
    for row in components:
        amount = Decimal(row.amount_decimal)
        if row.amount_unit == "uL":
            liquid_ul += amount
        elif row.amount_unit == "mL":
            liquid_ul += amount * Decimal("1000")
        elif row.amount_unit == "mg":
            solid_mg += amount
        elif row.amount_unit == "g":
            solid_mg += amount * Decimal("1000")
    return (
        decimal_text(liquid_ul, "liquid_total_ul", nonnegative=True),
        decimal_text(solid_mg, "solid_total_mg", nonnegative=True),
    )


def _assert_summary(
    components: tuple[FormulaComponentV1, ...],
    summary: Mapping[str, Any],
) -> tuple[str, str]:
    liquid = tuple(row for row in components if row.amount_unit in {"uL", "mL"})
    solid = tuple(row for row in components if row.amount_unit in {"mg", "g"})
    liquid_total, solid_total = _totals(components)
    expected = {
        "row_count": len(components),
        "liquid_row_count": len(liquid),
        "solid_row_count": len(solid),
        "liquid_total_ul": liquid_total,
        "solid_total_mg": solid_total,
    }
    for key, actual in expected.items():
        declared = summary.get(key)
        if key.endswith("_count"):
            if isinstance(declared, bool) or int(declared) != actual:
                raise SnapshotSourceError(f"declared {key} does not match rows")
        elif decimal_text(declared, key, nonnegative=True) != actual:
            raise SnapshotSourceError(f"declared {key} does not match rows")
    return liquid_total, solid_total


def load_r5_design_snapshot(
    path: Path = DEFAULT_R5_MANIFEST,
) -> FormulaSnapshotLoadV1:
    manifest = _load_json_object(path)
    if manifest.get("schema_version") != "lavande-ambre-profond-r5-design-comparator-v1":
        raise SnapshotSourceError("unsupported R5 comparator schema")
    if manifest.get("design_only") is not True:
        raise SnapshotSourceError("R5 source must remain design-only")
    rows = manifest.get("rows")
    if not isinstance(rows, list) or not rows:
        raise SnapshotSourceError("R5 comparator requires rows")
    row_hash = _canonical_hash(rows)
    if row_hash != manifest.get("canonical_formula_rows_sha256"):
        raise SnapshotSourceError("R5 canonical row hash mismatch")
    components = tuple(_manifest_row_component(row) for row in rows)
    liquid_total, solid_total = _assert_summary(components, manifest.get("summary", {}))
    snapshot = FormulaSnapshotV1(
        formula_id=str(manifest["comparator_id"]),
        formula_name=str(manifest["title"]),
        components=components,
        # The R4 hash is retained in the source manifest but its bytes were not
        # available, so it is deliberately not promoted into a verified parent
        # snapshot hash.
        parent_formula_sha256=None,
        design_only=True,
    )
    return FormulaSnapshotLoadV1(
        snapshot=snapshot,
        source_path=path.as_posix(),
        source_sha256=_file_sha256(path),
        source_schema_version=str(manifest["schema_version"]),
        canonical_rows_sha256=row_hash,
        liquid_total_ul_decimal=liquid_total,
        solid_total_mg_decimal=solid_total,
        validation_state="WITHHOLD_UNKNOWN",
        reason_codes=("PARENT_BYTES_NOT_AVAILABLE", "STOCK_LOTS_NOT_BOUND"),
    )


def load_r6_design_snapshot(
    path: Path = DEFAULT_R6_MANIFEST,
    *,
    parent_path: Path | None = None,
) -> FormulaSnapshotLoadV1:
    manifest = _load_json_object(path)
    if manifest.get("schema_version") != "lavande-ambre-profond-design-successor-delta-v1":
        raise SnapshotSourceError("unsupported R6 successor schema")
    if manifest.get("state") != "ADMITTED_DESIGN_SUCCESSOR_ONLY":
        raise SnapshotSourceError("R6 source must remain a design successor only")
    parent = manifest.get("parent")
    if not isinstance(parent, dict):
        raise SnapshotSourceError("R6 successor requires parent metadata")
    resolved_parent_path = parent_path or (ROOT / str(parent.get("path", "")))
    if _file_sha256(resolved_parent_path) != parent.get("sha256"):
        raise SnapshotSourceError("R6 parent manifest hash mismatch")
    parent_load = load_r5_design_snapshot(resolved_parent_path)
    parent_manifest = _load_json_object(resolved_parent_path)
    parent_rows = parent_manifest["rows"]
    replacement = manifest.get("row_replacement")
    if not isinstance(replacement, dict):
        raise SnapshotSourceError("R6 successor requires one row replacement")
    old_row = replacement.get("parent_row")
    new_row = replacement.get("successor_row")
    if not isinstance(old_row, dict) or not isinstance(new_row, dict):
        raise SnapshotSourceError("R6 row replacement is malformed")
    source_row = replacement.get("source_row")
    matches = [index for index, row in enumerate(parent_rows) if row == old_row]
    if len(matches) != 1 or old_row.get("source_row") != source_row:
        raise SnapshotSourceError("R6 parent row replacement does not match R5")
    successor_rows = [dict(row) for row in parent_rows]
    successor_rows[matches[0]] = dict(new_row)
    invariants = manifest.get("successor_invariants")
    if not isinstance(invariants, dict):
        raise SnapshotSourceError("R6 successor invariants are missing")
    if invariants.get("changed_source_rows") != [source_row]:
        raise SnapshotSourceError("R6 changed-row invariant mismatch")
    row_hash = _canonical_hash(successor_rows)
    if row_hash != invariants.get("successor_canonical_rows_sha256"):
        raise SnapshotSourceError("R6 canonical row hash mismatch")
    components = tuple(_manifest_row_component(row) for row in successor_rows)
    liquid_total, solid_total = _assert_summary(components, invariants)
    snapshot = FormulaSnapshotV1(
        formula_id=str(manifest["successor_id"]),
        formula_name=str(manifest["title"]),
        components=components,
        parent_formula_sha256=parent_load.snapshot.sha256,
        design_only=True,
    )
    return FormulaSnapshotLoadV1(
        snapshot=snapshot,
        source_path=path.as_posix(),
        source_sha256=_file_sha256(path),
        source_schema_version=str(manifest["schema_version"]),
        canonical_rows_sha256=row_hash,
        liquid_total_ul_decimal=liquid_total,
        solid_total_mg_decimal=solid_total,
        validation_state="WITHHOLD_UNKNOWN",
        reason_codes=(
            "DESIGN_SUCCESSOR_ONLY",
            "STOCK_LOTS_NOT_BOUND",
            "EXACT_RELEASE_CAPABILITY_NOT_BOUND",
        ),
    )


def _split_markdown_row(line: str) -> list[str]:
    values = [part.strip().replace("**", "").replace("`", "") for part in line.split("|")]
    if values and not values[0]:
        values = values[1:]
    if values and not values[-1]:
        values = values[:-1]
    return values


def _markdown_formula_rows(text: str) -> list[dict[str, Any]]:
    lines = text.splitlines()
    rows: list[dict[str, Any]] = []
    for index, line in enumerate(lines):
        if not line.lstrip().startswith("|") or index + 1 >= len(lines):
            continue
        separator = lines[index + 1].strip()
        if not re.fullmatch(r"\|[\s:\-|]+\|?", separator):
            continue
        headers = [
            re.sub(r"\s+", " ", value.lower().replace("µ", "u").replace("μ", "u"))
            for value in _split_markdown_row(line)
        ]
        if "ingredient" not in headers or "basket" not in headers or "#" not in headers:
            continue
        ingredient_idx = headers.index("ingredient")
        basket_idx = headers.index("basket")
        row_idx = headers.index("#")
        stock_idx = next(
            (i for i, header in enumerate(headers) if "dilution" in header or header == "form"),
            None,
        )
        amount_idx = next(
            (i for i, header in enumerate(headers) if header == "amount" or "amount (ul)" in header),
            None,
        )
        if stock_idx is None or amount_idx is None:
            continue
        header_unit = "uL" if "ul" in headers[amount_idx] else None
        cursor = index + 2
        while cursor < len(lines) and lines[cursor].lstrip().startswith("|"):
            cells = _split_markdown_row(lines[cursor])
            cursor += 1
            if max(ingredient_idx, basket_idx, row_idx, stock_idx, amount_idx) >= len(cells):
                continue
            if not re.fullmatch(r"\d+", cells[row_idx]):
                continue
            label = cells[ingredient_idx].strip()
            basket = cells[basket_idx].strip()
            stock = cells[stock_idx].strip()
            amount_cell = cells[amount_idx].strip()
            amount_match = re.fullmatch(
                r"([0-9][0-9,]*(?:\.[0-9]+)?)\s*(uL|[µμ]L|mL|mg|g)?",
                amount_cell,
                flags=re.IGNORECASE,
            )
            if not amount_match or not all((label, basket, stock)):
                raise SnapshotSourceError("malformed Markdown formula row")
            row_unit = header_unit or amount_match.group(2)
            if row_unit is None:
                raise SnapshotSourceError("Markdown amount unit is missing")
            rows.append(
                {
                    "source_row": int(cells[row_idx]),
                    "basket": basket,
                    "material": label,
                    "required_stock": stock,
                    "dose": decimal_text(
                        amount_match.group(1).replace(",", ""),
                        "dose",
                        positive=True,
                    ),
                    "unit": _unit(row_unit),
                    "evidence": f"MARKDOWN-ROW-{cells[row_idx]}",
                }
            )
    if not rows:
        raise SnapshotSourceError("no supported Markdown formula rows found")
    identifiers = [row["source_row"] for row in rows]
    if len(identifiers) != len(set(identifiers)):
        raise SnapshotSourceError("Markdown formula row identities are duplicated")
    return rows


def load_markdown_design_snapshot(
    path: Path,
    *,
    formula_id: str | None = None,
) -> FormulaSnapshotLoadV1:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise SnapshotSourceError(f"could not read Markdown snapshot {path}") from exc
    title_match = re.search(r"^#\s+(.+?)\s*$", text, flags=re.MULTILINE)
    if title_match is None:
        raise SnapshotSourceError("Markdown snapshot requires an H1 title")
    identity_match = re.search(r"\*\*Design identity:\*\*\s*`([^`]+)`", text)
    resolved_id = formula_id or (identity_match.group(1) if identity_match else None)
    if not resolved_id:
        raise SnapshotSourceError("Markdown snapshot requires a formula identity")
    rows = _markdown_formula_rows(text)
    components = tuple(_manifest_row_component(row) for row in rows)
    liquid_total, solid_total = _totals(components)
    declared_liquid = re.search(
        r"Liquid stock-charge target:\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*[uµμ]L",
        text,
        flags=re.IGNORECASE,
    )
    if declared_liquid is None or decimal_text(
        declared_liquid.group(1).replace(",", ""),
        "declared_liquid_total",
        nonnegative=True,
    ) != liquid_total:
        raise SnapshotSourceError("Markdown liquid total does not match rows")
    if Decimal(solid_total) <= 0:
        raise SnapshotSourceError("Markdown design must preserve a separate solid total")
    row_hash = _canonical_hash(rows)
    snapshot = FormulaSnapshotV1(
        formula_id=resolved_id,
        formula_name=title_match.group(1).strip(),
        components=components,
        parent_formula_sha256=None,
        design_only=True,
    )
    return FormulaSnapshotLoadV1(
        snapshot=snapshot,
        source_path=path.as_posix(),
        source_sha256=_file_sha256(path),
        source_schema_version="markdown-design-formula-v1",
        canonical_rows_sha256=row_hash,
        liquid_total_ul_decimal=liquid_total,
        solid_total_mg_decimal=solid_total,
        validation_state="WITHHOLD_UNKNOWN",
        reason_codes=(
            "COMPUTATIONAL_DESIGN_CANDIDATE",
            "STOCK_LOTS_NOT_BOUND",
            "NOT_SENSORY_TESTED",
        ),
    )


def load_parallel_a_design_snapshot(
    path: Path = DEFAULT_PARALLEL_A_FORMULA,
) -> FormulaSnapshotLoadV1:
    return load_markdown_design_snapshot(path)


__all__ = [
    "DEFAULT_PARALLEL_A_FORMULA",
    "DEFAULT_R5_MANIFEST",
    "DEFAULT_R6_MANIFEST",
    "FormulaSnapshotLoadV1",
    "SnapshotSourceError",
    "load_markdown_design_snapshot",
    "load_parallel_a_design_snapshot",
    "load_r5_design_snapshot",
    "load_r6_design_snapshot",
]
