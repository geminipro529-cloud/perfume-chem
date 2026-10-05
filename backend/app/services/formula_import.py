"""Parse formula Markdown files into lab domain models."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import Any

from app.core.config import PROJECT_ROOT


@dataclass
class ParsedComponent:
    material_name: str
    dilution: float  # active fraction (1.0 for neat, 0.1 for 10%, etc.)
    volume_ul: float
    role: str | None  # "top", "heart", "base", or None


@dataclass
class ImportResult:
    formula_name: str
    components: list[ParsedComponent]
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class FormulaImportParser:
    """Parse formula Markdown files into structured component data."""

    ROLE_KEYWORDS = {
        "top": "top",
        "heart": "heart",
        "base": "base",
    }

    @classmethod
    def parse_file(cls, path: Path) -> ImportResult:
        """Parse a formula Markdown file and return structured component data."""
        if not path.exists():
            return ImportResult(
                formula_name="",
                components=[],
                errors=[f"File not found: {path}"],
            )
        text = path.read_text(encoding="utf-8")
        return cls.parse_text(text, path.stem)

    @classmethod
    def parse_text(cls, text: str, default_name: str = "") -> ImportResult:
        """Parse Markdown text content."""
        lines = text.split("\n")
        warnings: list[str] = []
        errors: list[str] = []

        # Extract formula name from first heading
        formula_name = default_name
        for line in lines:
            m = re.match(r"^#\s+(.+)$", line.strip())
            if m:
                formula_name = m.group(1).strip()
                break

        # Parse section-based ingredients
        components: list[ParsedComponent] = []
        current_role: str | None = None
        header_skipped = False

        for line in lines:
            stripped = line.strip()

            # Section header detection
            section_match = re.match(r"^##\s+(.+)$", stripped)
            if section_match:
                section_name = section_match.group(1).strip().lower()
                current_role = None
                for keyword, role in cls.ROLE_KEYWORDS.items():
                    if keyword in section_name:
                        current_role = role
                        break
                header_skipped = False
                continue

            # Table row detection (starts with |)
            if stripped.startswith("|"):
                parts = [p.strip() for p in stripped.split("|")]
                # Remove empty first/last parts from split on leading/trailing |
                parts = [p for p in parts if p]

                # Check for bold section header rows (e.g. **🌅 Top**)
                # These can be single-cell rows like "| **🌅 Top** |" or multi-cell rows
                bold_header = None
                for p in parts:
                    if p.startswith("**") and p.endswith("**"):
                        bold_header = p
                        break
                if bold_header:
                    section_name = bold_header.strip("*").strip().lower()
                    current_role = None
                    for keyword, role in cls.ROLE_KEYWORDS.items():
                        if keyword in section_name:
                            current_role = role
                            break
                    header_skipped = False
                    continue

                # Skip rows without a digit (non-data rows like header, separator, etc.)
                if not re.search(r"\|\s*\d+\s*\|", stripped):
                    continue

                if not header_skipped:
                    # Check if this is a header row (has Ingredient in it)
                    if any("ingredient" in p.lower() or "material" in p.lower() for p in parts):
                        header_skipped = True
                        continue
                    header_skipped = True

                if len(parts) < 3:
                    continue

                # Extract material name (second column)
                material_name = parts[1].strip() if len(parts) > 1 else ""
                if not material_name:
                    continue

                # Extract dilution (third column)
                dilution_str = parts[2].strip() if len(parts) > 2 else "neat"
                dilution = cls._parse_dilution(dilution_str)
                if dilution is None:
                    warnings.append(
                        f"Skipping {material_name}: could not parse dilution from '{dilution_str}'"
                    )
                    continue

                # Extract amount in µL (fourth column)
                amount_str = parts[3].strip() if len(parts) > 3 else ""
                volume_ul = cls._parse_volume(amount_str)

                if volume_ul is None or volume_ul <= 0:
                    warnings.append(
                        f"Skipping {material_name}: could not parse volume from '{amount_str}'"
                    )
                    continue

                components.append(
                    ParsedComponent(
                        material_name=material_name,
                        dilution=dilution,
                        volume_ul=volume_ul,
                        role=current_role,
                    )
                )
                continue

            # Reset table state on blank lines
            if not stripped:
                header_skipped = False

        if not components:
            errors.append("No ingredient table rows found in the file")

        return ImportResult(
            formula_name=formula_name,
            components=components,
            warnings=warnings,
            errors=errors,
        )

    @classmethod
    def _parse_dilution(cls, text: str) -> float | None:
        """Parse dilution string to active fraction.

        Examples:
            "neat" -> 1.0
            "10%" -> 0.1
            "1%" -> 0.01
            "20%" -> 0.2
        """
        text = text.strip().lower()
        if text == "neat" or text == "-" or not text:
            return 1.0
        m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*%(?:\s+in\s+.+)?", text)
        if m:
            percentage = float(m.group(1))
            if 0 < percentage <= 100:
                return percentage / 100.0
        return None

    @classmethod
    def _parse_volume(cls, text: str) -> float | None:
        """Parse volume string to microliters.

        Examples:
            "100" -> 100.0
            "0.10" -> 0.10 (treats as mL if < 1, converts to µL...
                          actually Markdown uses both µL and mL columns)

        The format has two amount columns: Amount (µL) and Amount (mL).
        We read the first amount column (µL).
        """
        text = text.strip()
        if not text:
            return None
        # Remove commas, units
        text = re.sub(r"[,\sµμulm]+$", "", text, flags=re.IGNORECASE)
        try:
            value = float(text)
            return value
        except ValueError:
            return None


@dataclass(frozen=True, slots=True)
class ParsedAnalysisRow:
    """One read-only formula row for the goal-analysis workbench."""

    row_id: str
    material: str
    amount_decimal: str
    amount_unit: str
    concentration_fraction_decimal: str | None
    concentration_basis: str
    basket: str | None
    role: str | None
    operation: str

    def as_engine_dict(self) -> dict[str, Any]:
        return {
            "row_id": self.row_id,
            "material": self.material,
            "amount_decimal": self.amount_decimal,
            "amount_unit": self.amount_unit,
            "concentration_fraction_decimal": self.concentration_fraction_decimal,
            "concentration_basis": self.concentration_basis,
            "basket": self.basket,
            "role": self.role,
            "operation": self.operation,
        }


@dataclass(slots=True)
class AnalysisImportResult:
    formula_name: str
    rows: list[ParsedAnalysisRow]
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class FormulaAnalysisImportParser:
    """Parse common Markdown formula tables without inventing physical facts.

    Unlike the historical import parser above, this read-only parser preserves
    both volume and mass rows.  It is intentionally not an inventory importer:
    ambiguous stock bases stay ``UNKNOWN`` and designs remain non-executable.
    """

    _AMOUNT_HEADER_TOKENS = ("amount", "dose", "volume", "mass", "quantity")
    _VALID_UNITS = {"uL", "mL", "mg", "g"}

    @staticmethod
    def _cells(line: str) -> list[str]:
        return [cell.strip() for cell in line.strip().strip("|").split("|")]

    @staticmethod
    def _plain(value: str) -> str:
        text = value.strip().replace("**", "").replace("`", "")
        return re.sub(r"<[^>]+>", " ", text).strip()

    @classmethod
    def _normalized(cls, value: str) -> str:
        return re.sub(
            r"\s+",
            " ",
            cls._plain(value).replace("µ", "u").replace("μ", "u").casefold(),
        ).strip()

    @staticmethod
    def _is_separator(line: str) -> bool:
        return bool(re.fullmatch(r"\s*\|?[\s:|-]+\|?\s*", line))

    @classmethod
    def _header_unit(cls, value: str) -> str | None:
        text = cls._normalized(value)
        if re.search(r"(?:\(|\b)ul(?:\)|\b)", text):
            return "uL"
        if re.search(r"(?:\(|\b)ml(?:\)|\b)", text):
            return "mL"
        if re.search(r"(?:\(|\b)mg(?:\)|\b)", text):
            return "mg"
        if re.search(r"(?:\(|\b)g(?:\)|\b)", text):
            return "g"
        return None

    @staticmethod
    def _decimal_text(value: Decimal) -> str:
        rendered = format(value, "f")
        return rendered.rstrip("0").rstrip(".") if "." in rendered else rendered

    @classmethod
    def _parse_amount(
        cls,
        value: str,
        header_unit: str | None,
    ) -> tuple[str, str] | None:
        text = cls._plain(value).replace("µ", "u").replace("μ", "u")
        match = re.search(r"[-+]?(?:\d[\d,\s]*(?:\.\d+)?|\.\d+)", text)
        if not match:
            return None
        try:
            amount = Decimal(match.group(0).replace(",", "").replace(" ", ""))
        except InvalidOperation:
            return None
        if not amount.is_finite() or amount <= 0:
            return None
        remainder = text[match.end() :].strip().casefold()
        inline_unit: str | None = None
        if re.match(r"^u\s*l\b|^ul\b", remainder):
            inline_unit = "uL"
        elif re.match(r"^ml\b", remainder):
            inline_unit = "mL"
        elif re.match(r"^mg\b", remainder):
            inline_unit = "mg"
        elif re.match(r"^g\b", remainder):
            inline_unit = "g"
        unit = inline_unit or header_unit
        if unit not in cls._VALID_UNITS:
            return None
        return cls._decimal_text(amount), unit

    @classmethod
    def _parse_concentration(cls, value: str | None) -> tuple[str | None, str]:
        if value is None:
            return None, "UNKNOWN"
        text = cls._normalized(value)
        percent = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
        if percent:
            amount = Decimal(percent.group(1)) / Decimal(100)
            if amount <= 0 or amount > 1:
                return None, "UNKNOWN"
            if "w/w" in text or "w-w" in text:
                basis = "W_W"
            elif "v/v" in text or "v-v" in text:
                basis = "V_V"
            else:
                basis = "UNKNOWN"
            return cls._decimal_text(amount), basis
        if any(token in text for token in ("neat", "undiluted", "as supplied")):
            return "1", "NEAT"
        return None, "UNKNOWN"

    @classmethod
    def parse_text(
        cls,
        text: str,
        *,
        default_name: str,
        source_sha256: str,
    ) -> AnalysisImportResult:
        lines = text.splitlines()
        formula_name = default_name
        warnings: list[str] = []
        errors: list[str] = []
        rows: list[ParsedAnalysisRow] = []
        current_role: str | None = None
        header: list[str] | None = None
        header_line = 0

        for source_line, line in enumerate(lines, start=1):
            heading = re.match(r"^\s*#\s+(.+?)\s*$", line)
            if heading and formula_name == default_name:
                formula_name = cls._plain(heading.group(1))[:255]
            section = re.match(r"^\s*##+\s+(.+?)\s*$", line)
            if section:
                section_name = cls._normalized(section.group(1))
                current_role = next(
                    (role for role in ("top", "heart", "base") if role in section_name),
                    None,
                )
                header = None
                continue
            if not line.strip().startswith("|"):
                if line.strip():
                    header = None
                continue
            if cls._is_separator(line):
                continue

            cells = cls._cells(line)
            normalized_cells = [cls._normalized(cell) for cell in cells]
            material_candidates = [
                index
                for index, cell in enumerate(normalized_cells)
                if re.search(r"\b(?:ingredient|material)\b", cell)
                and "role" not in cell
            ]
            amount_candidates = [
                index
                for index, cell in enumerate(normalized_cells)
                if any(token in cell for token in cls._AMOUNT_HEADER_TOKENS)
            ]
            if material_candidates and amount_candidates:
                header = cells
                header_line = source_line
                continue
            if header is None:
                continue

            normalized_header = [cls._normalized(cell) for cell in header]
            material_index = next(
                (
                    index
                    for index, cell in enumerate(normalized_header)
                    if re.search(r"\b(?:ingredient|material)\b", cell)
                    and "role" not in cell
                ),
                None,
            )
            if material_index is None or material_index >= len(cells):
                continue
            material = cls._plain(cells[material_index])
            if not material or "total" in cls._normalized(material):
                continue

            indexed_amounts: list[tuple[int, str | None]] = []
            for index, cell in enumerate(normalized_header):
                if any(token in cell for token in cls._AMOUNT_HEADER_TOKENS):
                    indexed_amounts.append((index, cls._header_unit(header[index])))
            # Prefer the explicit uL representation when a table repeats the
            # same transfer in both uL and mL columns.
            indexed_amounts.sort(
                key=lambda item: ({"uL": 0, "mg": 1, "g": 2, "mL": 3, None: 4}[item[1]], item[0])
            )
            parsed_amount: tuple[str, str] | None = None
            for amount_index, header_unit in indexed_amounts:
                if amount_index < len(cells):
                    parsed_amount = cls._parse_amount(cells[amount_index], header_unit)
                if parsed_amount is not None:
                    break
            if parsed_amount is None:
                warnings.append(
                    f"Skipped line {source_line}: no positive amount with an explicit supported unit for {material}."
                )
                continue

            dilution_index = next(
                (
                    index
                    for index, cell in enumerate(normalized_header)
                    if "dilution" in cell
                    or "stock strength" in cell
                    or "owned stock" in cell
                    or cell == "form"
                ),
                None,
            )
            dilution_text = (
                cells[dilution_index]
                if dilution_index is not None and dilution_index < len(cells)
                else None
            )
            fraction, basis = cls._parse_concentration(dilution_text)
            basket_index = next(
                (index for index, cell in enumerate(normalized_header) if cell == "basket"),
                None,
            )
            basket = (
                cls._plain(cells[basket_index])[:40]
                if basket_index is not None and basket_index < len(cells)
                else None
            )
            role_index = next(
                (
                    index
                    for index, cell in enumerate(normalized_header)
                    if "role" in cell or cell in {"note", "purpose"}
                ),
                None,
            )
            role = (
                cls._plain(cells[role_index])[:500]
                if role_index is not None and role_index < len(cells)
                else current_role
            )
            amount_decimal, amount_unit = parsed_amount
            rows.append(
                ParsedAnalysisRow(
                    row_id=f"project-{source_sha256[:12]}-{source_line}-{len(rows) + 1}",
                    material=material[:255],
                    amount_decimal=amount_decimal,
                    amount_unit=amount_unit,
                    concentration_fraction_decimal=fraction,
                    concentration_basis=basis,
                    basket=basket or None,
                    role=role or None,
                    operation=(
                        "MASS_ADD" if amount_unit in {"mg", "g"} else "DIRECT_ADD"
                    ),
                )
            )

        if not rows:
            errors.append("No formula rows with explicit material, amount, and unit were found.")
        if len(rows) > 500:
            errors.append("The formula contains more than the 500-row analysis limit.")
            rows = []
        if header_line and not formula_name:
            formula_name = default_name
        return AnalysisImportResult(
            formula_name=formula_name or default_name,
            rows=rows,
            warnings=warnings,
            errors=errors,
        )


class FormulaAnalysisLibrary:
    """Read-only access to Markdown formulas already stored in this project."""

    MAX_SOURCE_BYTES = 2_000_000

    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or (PROJECT_ROOT / "formulas")).resolve()

    def list_sources(self) -> list[dict[str, Any]]:
        if not self.root.is_dir():
            return []
        sources: list[dict[str, Any]] = []
        for path in self.root.rglob("*.md"):
            resolved = path.resolve()
            if not resolved.is_file() or not resolved.is_relative_to(self.root):
                continue
            relative = resolved.relative_to(self.root).as_posix()
            label = str(PurePosixPath(relative).with_suffix(""))
            sources.append(
                {
                    "source_path": relative,
                    "display_name": label.replace("_", " ").replace("/", " › "),
                    "size_bytes": resolved.stat().st_size,
                    "design_only": True,
                }
            )
        return sorted(sources, key=lambda item: str(item["display_name"]).casefold())

    def load_source(self, source_path: str) -> dict[str, Any]:
        raw = str(source_path).strip()
        if not raw or len(raw) > 500 or "\\" in raw:
            raise ValueError("Choose a valid project formula path.")
        relative = PurePosixPath(raw)
        if relative.is_absolute() or ".." in relative.parts or relative.suffix.casefold() != ".md":
            raise ValueError("Only relative Markdown files inside the project formula library are allowed.")
        resolved = self.root.joinpath(*relative.parts).resolve()
        if not resolved.is_relative_to(self.root) or not resolved.is_file():
            raise ValueError("The selected project formula was not found.")
        source_bytes = resolved.read_bytes()
        if len(source_bytes) > self.MAX_SOURCE_BYTES:
            raise ValueError("The selected project formula exceeds the read-only analysis size limit.")
        try:
            text = source_bytes.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ValueError("The selected project formula is not UTF-8 text.") from error
        source_hash = sha256(source_bytes).hexdigest()
        result = FormulaAnalysisImportParser.parse_text(
            text,
            default_name=relative.stem,
            source_sha256=source_hash,
        )
        if result.errors:
            raise ValueError(" ".join(result.errors))

        liquid_total_ul = Decimal(0)
        mass_total_mg = Decimal(0)
        for row in result.rows:
            amount = Decimal(row.amount_decimal)
            if row.amount_unit == "uL":
                liquid_total_ul += amount
            elif row.amount_unit == "mL":
                liquid_total_ul += amount * Decimal(1000)
            elif row.amount_unit == "mg":
                mass_total_mg += amount
            elif row.amount_unit == "g":
                mass_total_mg += amount * Decimal(1000)

        return {
            "schema_version": "workbench-formula-source-v1",
            "source_path": relative.as_posix(),
            "source_sha256": source_hash,
            "formula_name": result.formula_name,
            "rows": [row.as_engine_dict() for row in result.rows],
            "warnings": result.warnings,
            "separate_totals": {
                "liquid_total_ul": self._render_total(liquid_total_ul),
                "mass_total_mg": self._render_total(mass_total_mg),
            },
            "design_only": True,
            "inventory_modified": False,
            "release_authority": False,
            "safety_authority": False,
            "compounding_authority": False,
            "evidence_admission_authorized": False,
        }

    @staticmethod
    def _render_total(value: Decimal) -> str:
        rendered = format(value, "f")
        return rendered.rstrip("0").rstrip(".") if "." in rendered else rendered
