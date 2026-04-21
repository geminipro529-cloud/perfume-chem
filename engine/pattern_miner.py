"""Formulation pattern miner — parses formulation .md files to extract
ingredient usage patterns, frequencies, and co-occurrence data.

Feeds the feedback loop with historical formulation data so the engine
can learn which ingredients are commonly paired and in what ratios.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

FORMULATIONS_DIR = Path(__file__).resolve().parent.parent / "formulations"

# Regex to match markdown table rows: | ingredient | amount | ...
TABLE_ROW_RE = re.compile(
    r"^\|\s*\*{0,2}(.+?)\*{0,2}\s*\|\s*([\d.]+)\s*(mL|ml|g|drops|%)",
    re.IGNORECASE,
)

# Skip header/separator rows
SKIP_RE = re.compile(r"^\|[\s\-:]+\|")
HEADER_RE = re.compile(r"^\|\s*\*{0,2}(Component|Ingredient|Material)\*{0,2}\s*\|", re.IGNORECASE)


@dataclass
class ParsedIngredient:
    name: str
    amount: float
    unit: str


@dataclass
class ParsedFormulation:
    filepath: str
    title: str
    date: str | None
    ingredients: list[ParsedIngredient] = field(default_factory=list)


@dataclass
class MiningReport:
    formulations: list[ParsedFormulation]
    ingredient_frequency: dict[str, int]
    co_occurrences: dict[str, dict[str, int]]
    avg_amounts: dict[str, float]

    def summary(self) -> dict:
        return {
            "total_formulations": len(self.formulations),
            "unique_ingredients": len(self.ingredient_frequency),
            "most_used": sorted(
                self.ingredient_frequency.items(), key=lambda x: x[1], reverse=True
            )[:20],
        }

    def to_markdown(self) -> str:
        lines = ["# Formulation Pattern Mining Report\n"]
        s = self.summary()
        lines.append(f"**Formulations parsed:** {s['total_formulations']}")
        lines.append(f"**Unique ingredients:** {s['unique_ingredients']}\n")

        lines.append("## Top 20 Most-Used Ingredients\n")
        lines.append("| Ingredient | Appearances | Avg Amount |")
        lines.append("|---|---|---|")
        for name, count in s["most_used"]:
            avg = self.avg_amounts.get(name, 0)
            lines.append(f"| {name} | {count} | {avg:.2f} |")
        lines.append("")

        # Top co-occurrences
        pairs: list[tuple[str, str, int]] = []
        seen: set[tuple[str, str]] = set()
        for a, partners in self.co_occurrences.items():
            for b, count in partners.items():
                key = tuple(sorted((a, b)))
                if key not in seen and count >= 3:
                    seen.add(key)
                    pairs.append((a, b, count))
        pairs.sort(key=lambda x: x[2], reverse=True)

        if pairs:
            lines.append("## Top Co-Occurring Pairs (≥3 appearances)\n")
            lines.append("| Material A | Material B | Co-occurrences |")
            lines.append("|---|---|---|")
            for a, b, count in pairs[:30]:
                lines.append(f"| {a} | {b} | {count} |")
            lines.append("")

        return "\n".join(lines)


def _normalize_name(name: str) -> str:
    """Normalize ingredient name for consistent matching."""
    name = name.strip().strip("*").strip()
    # Remove bold markdown
    name = re.sub(r"\*{1,2}", "", name)
    # Remove trailing colons or dashes
    name = name.rstrip(":- ")
    return name


def _extract_date(filepath: Path) -> str | None:
    """Extract date from filename like '2025-12-13_...'."""
    match = re.match(r"(\d{4}-\d{2}-\d{2})", filepath.name)
    return match.group(1) if match else None


def _extract_title(content: str) -> str:
    """Extract title from first markdown heading."""
    for line in content.split("\n"):
        if line.startswith("# "):
            return line.lstrip("# ").strip()
    return "Untitled"


# Ingredients to skip (solvents, headers, etc.)
SKIP_INGREDIENTS = {
    "ethanol", "ethanol 99%", "dpg", "dipropylene glycol",
    "total", "totals", "solvent", "component", "ingredient",
    "material", "amount", "base", "",
}


def parse_formulation(filepath: Path) -> ParsedFormulation:
    """Parse a single formulation .md file."""
    content = filepath.read_text(encoding="utf-8", errors="replace")
    title = _extract_title(content)
    date = _extract_date(filepath)

    ingredients: list[ParsedIngredient] = []
    in_table = False

    for line in content.split("\n"):
        stripped = line.strip()

        # Skip separators and headers
        if SKIP_RE.match(stripped) or HEADER_RE.match(stripped):
            in_table = True
            continue

        if not stripped.startswith("|"):
            if in_table:
                in_table = False
            continue

        match = TABLE_ROW_RE.match(stripped)
        if match:
            name = _normalize_name(match.group(1))
            try:
                amount = float(match.group(2))
            except ValueError:
                continue
            unit = match.group(3).lower()

            if name.lower() in SKIP_INGREDIENTS:
                continue

            ingredients.append(ParsedIngredient(name=name, amount=amount, unit=unit))

    return ParsedFormulation(
        filepath=str(filepath.relative_to(filepath.parent.parent)),
        title=title,
        date=date,
        ingredients=ingredients,
    )


def mine_patterns(formulations_dir: Path | None = None) -> MiningReport:
    """Parse all formulation files and extract usage patterns."""
    fdir = formulations_dir or FORMULATIONS_DIR
    if not fdir.exists():
        return MiningReport(
            formulations=[], ingredient_frequency={},
            co_occurrences={}, avg_amounts={},
        )

    formulations: list[ParsedFormulation] = []
    for md_file in sorted(fdir.glob("*.md")):
        parsed = parse_formulation(md_file)
        if parsed.ingredients:
            formulations.append(parsed)

    # Aggregate statistics
    freq: dict[str, int] = {}
    amounts: dict[str, list[float]] = {}
    co_occur: dict[str, dict[str, int]] = {}

    for form in formulations:
        names = [i.name for i in form.ingredients]
        for ing in form.ingredients:
            freq[ing.name] = freq.get(ing.name, 0) + 1
            amounts.setdefault(ing.name, []).append(ing.amount)

        # Co-occurrence
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                if a == b:
                    continue
                co_occur.setdefault(a, {})
                co_occur[a][b] = co_occur[a].get(b, 0) + 1
                co_occur.setdefault(b, {})
                co_occur[b][a] = co_occur[b].get(a, 0) + 1

    avg_amounts = {
        name: round(sum(vals) / len(vals), 3)
        for name, vals in amounts.items()
    }

    return MiningReport(
        formulations=formulations,
        ingredient_frequency=freq,
        co_occurrences=co_occur,
        avg_amounts=avg_amounts,
    )


if __name__ == "__main__":
    report = mine_patterns()
    print(report.to_markdown())
