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
    # Header text of the column the amount was read from (provenance only;
    # not part of the engine payload).
    amount_header: str = ""

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
    # A header that is only a unit ("µL", "mg"), a raw-stock unit ("Raw µL")
    # or an addition column ("Add", "Add (µL)") names the stock amount.  The
    # unit still has to come from the header or the cell; "Add" alone never
    # supplies one.
    _UNIT_ONLY_HEADER = re.compile(r"(?:(?:raw|stock)\s+)?\(?(?:ul|ml|mg|g)\)?")
    _ADD_HEADER = re.compile(r"add(?:\s*\((?:ul|ml|mg|g)\)|\s+(?:ul|ml|mg|g))?")
    _EXPECTED_AMOUNT_HINT = "Use a column named µL, mg, g, Raw µL or Amount."

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

    @classmethod
    def _amount_column_kind(cls, normalized: str) -> str | None:
        """Classify a normalized header cell as a stock or active amount column.

        Returns ``"stock"`` for a column holding the stock (raw) amount,
        ``"active"`` for an active-material amount that must never be read as
        the stock amount, and ``None`` for any other column.
        """
        if re.search(r"\bact(?:ive)?\b", normalized):
            return "active"
        if any(token in normalized for token in cls._AMOUNT_HEADER_TOKENS):
            return "stock"
        if cls._UNIT_ONLY_HEADER.fullmatch(normalized) or cls._ADD_HEADER.fullmatch(normalized):
            return "stock"
        return None

    @staticmethod
    def _decimal_text(value: Decimal) -> str:
        rendered = format(value, "f")
        return rendered.rstrip("0").rstrip(".") if "." in rendered else rendered

    _AMOUNT_NUMBER = re.compile(r"[-+]?(?:\d[\d,\s]*(?:\.\d+)?|\.\d+)")

    @classmethod
    def _amount_text(cls, value: str) -> str:
        """The cell without parenthesised notes ("60 (was 50)" -> "60")."""
        text = cls._plain(value).replace("µ", "u").replace("μ", "u")
        return re.sub(r"\([^)]*\)", " ", text).strip()

    @classmethod
    def _has_several_numbers(cls, value: str) -> bool:
        return len(cls._AMOUNT_NUMBER.findall(cls._amount_text(value))) > 1

    @classmethod
    def _parse_amount(
        cls,
        value: str,
        header_unit: str | None,
    ) -> tuple[str, str] | None:
        text = cls._amount_text(value)
        match = cls._AMOUNT_NUMBER.search(text)
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

    @staticmethod
    def _basis_of(text: str) -> str:
        if "w/w" in text or "w-w" in text:
            return "W_W"
        if "v/v" in text or "v-v" in text:
            return "V_V"
        return "UNKNOWN"

    @classmethod
    def _parse_concentration(
        cls, value: str | None, header: str | None = None
    ) -> tuple[str | None, str]:
        if value is None:
            return None, "UNKNOWN"
        text = cls._normalized(value)
        if text.startswith(("neat", "as supplied")):
            return "1", "NEAT"
        ratio = re.match(r"1\s*[:/]\s*(\d+(?:\.\d+)?)(?![\d.])", text)
        if ratio:
            divisor = Decimal(ratio.group(1))
            if divisor < 1:
                return None, "UNKNOWN"
            return cls._decimal_text(Decimal(1) / divisor), cls._basis_of(text)
        percent = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
        if percent:
            amount = Decimal(percent.group(1)) / Decimal(100)
            if amount <= 0 or amount > 1:
                return None, "UNKNOWN"
            return cls._decimal_text(amount), cls._basis_of(text)
        if any(token in text for token in ("neat", "undiluted", "as supplied")):
            return "1", "NEAT"
        if re.fullmatch(r"\d+(?:\.\d+)?", text):
            number = Decimal(text)
            if header is not None and "%" in header:
                number /= Decimal(100)
                if 0 < number <= 1:
                    return cls._decimal_text(number), "UNKNOWN"
            elif 0 < number < 1:
                return cls._decimal_text(number), "UNKNOWN"
            elif number == 1:
                return "1", "NEAT"
        return None, "UNKNOWN"

    # A trailing strength or dilution note on a material name ("10%",
    # "10% in DPG", "(neat)") does not make it a different material.
    _TRAILING_STRENGTH = re.compile(
        r"\s*\(?\s*(?:\d+(?:\.\d+)?\s*%(?:\s*(?:w/w|v/v|w/v))?(?:\s+in\s+[a-z][\w\s-]*?)?"
        r"|neat|undiluted)\s*\)?\s*$"
    )
    # Ethanol is the final dilution, not part of the concentrate.  Other
    # carriers (DPG, DEP, IPM, TEC) can be real concentrate rows and stay.
    _ETHANOL_NAME = re.compile(r"(?:ethanol|ethyl alcohol|perfumer'?s alcohol|alcohol)\b(?!\s*c\s*-?\d)")

    @classmethod
    def _material_key(cls, value: str) -> str:
        key = cls._normalized(value).replace("*", "").replace("_", " ").strip()
        while True:
            stripped = cls._TRAILING_STRENGTH.sub("", key).strip()
            if stripped == key or not stripped:
                return key
            key = stripped

    @staticmethod
    def _table_label(line: int, heading: str | None) -> str:
        if heading:
            return f'the table under "{heading}" (line {line})'
        return f"the table at line {line}"

    @staticmethod
    def _amount_differences(
        table_rows: list[ParsedAnalysisRow],
        keys: list[str],
        first_kept: dict[str, ParsedAnalysisRow],
        first_seen: dict[str, int],
        limit: int = 3,
    ) -> str:
        """Name the restated amounts that disagree with the rows already read."""

        def comparable(row: ParsedAnalysisRow) -> tuple[Decimal, str]:
            amount = Decimal(row.amount_decimal)
            if row.amount_unit == "mL":
                return amount * 1000, "uL"
            return amount, row.amount_unit

        found = [
            f"{row.material} {row.amount_decimal} {row.amount_unit} here, "
            f"{first_kept[key].amount_decimal} {first_kept[key].amount_unit} at line {first_seen[key]}"
            for row, key in zip(table_rows, keys, strict=True)
            if comparable(row) != comparable(first_kept[key])
        ]
        if len(found) > limit:
            return "; ".join(found[:limit]) + f"; and {len(found) - limit} more"
        return "; ".join(found)

    @classmethod
    def _without_restated_tables(
        cls,
        rows: list[ParsedAnalysisRow],
        row_tables: list[int],
        table_headings: dict[int, str | None],
        addition_tables: set[int],
        warnings: list[str],
        errors: list[str],
    ) -> list[ParsedAnalysisRow]:
        """Keep each amount once when a file restates, summarizes or breaks down its build.

        Formula notes often restate the build as a summary or bench table;
        reading both would count materials twice.  A later table whose
        materials were all read already is skipped with a warning.  A later
        table that repeats some materials and adds others is ambiguous and
        refuses the import.  A table of new names whose amounts add up to
        exactly one row already read breaks that row down and is skipped.
        Additions to an existing bottle may repeat materials and are kept.
        """
        kept: list[ParsedAnalysisRow] = []
        first_seen: dict[str, int] = {}
        first_kept: dict[str, ParsedAnalysisRow] = {}
        kept_additions: list[int] = []
        for table_line in dict.fromkeys(row_tables):
            table_rows = [
                row for row, line in zip(rows, row_tables, strict=True) if line == table_line
            ]
            label = cls._table_label(table_line, table_headings.get(table_line))
            keys = [cls._material_key(row.material) for row in table_rows]
            repeated = [key for key in dict.fromkeys(keys) if key in first_seen]
            if kept and table_line not in addition_tables:
                if repeated and len(repeated) == len(set(keys)):
                    differences = cls._amount_differences(table_rows, keys, first_kept, first_seen)
                    note = (
                        f" Its amounts differ from the rows already read ({differences}); "
                        "check which is right."
                        if differences
                        else ""
                    )
                    warnings.append(
                        f"Skipped {label}: every material in it was already read above, "
                        f"so it restates the formula rather than adding to it.{note}"
                    )
                    continue
                if repeated:
                    places = ", ".join(
                        f"{table_rows[keys.index(key)].material} (line {first_seen[key]})"
                        for key in repeated
                    )
                    errors.append(
                        f"{label[0].upper()}{label[1:]} repeats materials already read: {places}. "
                        "It may be a summary or an older version; list each material once so "
                        "nothing is counted twice."
                    )
                    continue
                units = {row.amount_unit for row in table_rows}
                if len(table_rows) > 1 and len(units) == 1:
                    unit = units.pop()
                    table_sum = sum(Decimal(row.amount_decimal) for row in table_rows)
                    whole = next(
                        (
                            row
                            for row in kept
                            if row.amount_unit == unit and Decimal(row.amount_decimal) == table_sum
                        ),
                        None,
                    )
                    if whole is not None:
                        warnings.append(
                            f"Skipped {label}: its amounts add up to the {whole.amount_decimal} "
                            f"{unit} of {whole.material} already read, so it breaks that row down."
                        )
                        continue
            kept.extend(table_rows)
            if table_line in addition_tables:
                kept_additions.append(table_line)
            for key, row in zip(keys, table_rows, strict=True):
                first_seen.setdefault(key, table_line)
                first_kept.setdefault(key, row)
        if kept_additions:
            lines = ", ".join(str(line) for line in kept_additions)
            warnings.append(
                f"The rows from the table(s) at line {lines} are additions to an existing "
                "bottle, so the total is the amount added, not a whole bottle."
            )
        return kept

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
        row_tables: list[int] = []
        section_heading: str | None = None
        table_headings: dict[int, str | None] = {}
        # Tables whose rows are additions to an existing bottle: an Add
        # column, or a section about adding to an existing bottle.
        addition_tables: set[int] = set()
        # Heading level of an enclosing "existing bottle" section, if any.
        addition_section_level: int | None = None
        # The first material table whose header had no usable stock amount
        # column, kept to explain an empty result.
        unusable_header: tuple[list[str], bool] | None = None

        for source_line, line in enumerate(lines, start=1):
            heading = re.match(r"^\s*#\s+(.+?)\s*$", line)
            if heading and formula_name == default_name:
                formula_name = cls._plain(heading.group(1))[:255]
            section = re.match(r"^\s*(##+)\s+(.+?)\s*$", line)
            if section:
                section_name = cls._normalized(section.group(2))
                if section_name.startswith("pipeline analysis"):
                    # An appended pipeline report repeats the formula in its
                    # headspace table (Raw µL / Act µL); it is not a formula.
                    break
                section_heading = cls._plain(section.group(2))[:120]
                level = len(section.group(1))
                if addition_section_level is not None and level <= addition_section_level:
                    addition_section_level = None
                if addition_section_level is None and "existing bottle" in section_name:
                    addition_section_level = level
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
            column_kinds = [cls._amount_column_kind(cell) for cell in normalized_cells]
            if material_candidates and "stock" in column_kinds:
                header = cells
                header_line = source_line
                table_headings[header_line] = section_heading
                if addition_section_level is not None:
                    addition_tables.add(header_line)
                continue
            if material_candidates and not re.search(r"\d", "".join(normalized_cells)):
                # A new material table without a stock column (for example
                # Active µL only) ends the previous table; its amounts must
                # not be read under the previous header.
                header = None
                if unusable_header is None:
                    unusable_header = (cells, "active" in column_kinds)
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
            if cls._ETHANOL_NAME.match(cls._material_key(material)):
                warnings.append(
                    f"Skipped line {source_line}: {material} is the final dilution, "
                    "not part of the concentrate."
                )
                continue

            indexed_amounts: list[tuple[int, str | None]] = []
            for index, cell in enumerate(normalized_header):
                if cls._amount_column_kind(cell) == "stock":
                    indexed_amounts.append((index, cls._header_unit(header[index])))
            # Prefer the explicit uL representation when a table repeats the
            # same transfer in both uL and mL columns.
            indexed_amounts.sort(
                key=lambda item: ({"uL": 0, "mg": 1, "g": 2, "mL": 3, None: 4}[item[1]], item[0])
            )
            parsed_amount: tuple[str, str] | None = None
            ambiguous_amount: str | None = None
            amount_header = ""
            for amount_index, header_unit in indexed_amounts:
                if amount_index < len(cells):
                    if cls._has_several_numbers(cells[amount_index]):
                        ambiguous_amount = cls._plain(cells[amount_index])
                        break
                    parsed_amount = cls._parse_amount(cells[amount_index], header_unit)
                if parsed_amount is not None:
                    amount_header = cls._plain(header[amount_index])
                    break
            if ambiguous_amount is not None:
                warnings.append(
                    f"Skipped line {source_line}: amount '{ambiguous_amount}' for {material} "
                    "has more than one number; write a single amount (put notes in parentheses)."
                )
                continue
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
            fraction, basis = cls._parse_concentration(
                dilution_text,
                header[dilution_index] if dilution_index is not None else None,
            )
            if fraction is None and dilution_text is not None and cls._plain(dilution_text):
                warnings.append(
                    f"Strength '{cls._plain(dilution_text)}' for {material} can't be read; "
                    "write it like 10% w/w in DPG"
                )
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
            if cls._ADD_HEADER.fullmatch(cls._normalized(amount_header)):
                addition_tables.add(header_line)
            row_tables.append(header_line)
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
                    amount_header=amount_header,
                )
            )

        rows = cls._without_restated_tables(
            rows, row_tables, table_headings, addition_tables, warnings, errors
        )
        if not rows:
            if unusable_header is not None:
                found_cells, has_active = unusable_header
                found = ", ".join(cls._plain(cell) for cell in found_cells if cls._plain(cell))
                if has_active:
                    errors.append(
                        f"Found columns {found} but the only amount column is an active amount. "
                        "Active amounts are not stock amounts; add the stock amount as a Raw µL column."
                    )
                else:
                    errors.append(
                        f"Found columns {found} but no amount column. {cls._EXPECTED_AMOUNT_HINT}"
                    )
            else:
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
