"""Parse formula Markdown files into lab domain models."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


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
