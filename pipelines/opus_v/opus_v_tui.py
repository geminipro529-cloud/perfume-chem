"""Opus V — Rich Terminal Interface

Interactive TUI for scoring Top / Heart / Base pyramid ratios
through the 10-axis perfumery pipeline.

Usage:
    python opus_v_tui.py
"""
import sys, io
from pathlib import Path
from dataclasses import dataclass

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))  # workspace root
sys.path.insert(0, str(Path(__file__).resolve().parent))                # pipelines/opus_v

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import re, json, glob

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich.prompt import Prompt, IntPrompt
from rich import box

from engine.optimizer.scoring import FormulaScorer
from engine.optimizer.models import classify_note, FormulaVector
from engine.formula_analyzer import FormulaInfo, formula_to_vector, parse_formulas
from engine.synergy_graph import SynergyGraph

# Import formula data from the THB scorer module
from opus_v_thb_scorer import (
    TOP, HEART, BASE, MODULES, DILUTIONS, PRESETS,
    compute_original_totals, blend_modules, score_blend, AXES,
)

console = Console()

# ── Axis display config ──
AXIS_COLORS = {
    "longevity":          "bright_green",
    "sillage":            "bright_cyan",
    "synergy":            "bright_magenta",
    "luxury":             "gold1",
    "texture":            "medium_purple1",
    "stacking_depth":     "dark_orange",
    "hedonic":            "hot_pink",
    "skin_performance":   "salmon1",
    "perceptual_clarity": "sky_blue1",
    "safety":             "bright_red",
}

AXIS_ICONS = {
    "longevity":          "⏱",
    "sillage":            "💨",
    "synergy":            "🔗",
    "luxury":             "💎",
    "texture":            "🧵",
    "stacking_depth":     "📚",
    "hedonic":            "🌸",
    "skin_performance":   "🧴",
    "perceptual_clarity": "🔬",
    "safety":             "🛡",
}

DISPLAY_AXES = [a for a in AXES if a != "safety"]


# ─────────────────────────────────────────────────────────────────
# DISPLAY HELPERS
# ─────────────────────────────────────────────────────────────────

def score_color(v: float) -> str:
    if v >= 85: return "bold bright_green"
    if v >= 70: return "green"
    if v >= 55: return "yellow"
    if v >= 40: return "dark_orange"
    return "bold red"


def bar_chart(value: float, width: int = 30, color: str = "green") -> Text:
    filled = int(value / 100 * width)
    empty = width - filled
    t = Text()
    t.append("█" * filled, style=color)
    t.append("░" * empty, style="bright_black")
    t.append(f" {value:.1f}", style=score_color(value))
    return t


def build_axis_panel(name: str, ratios: list[int], scores: dict) -> Panel:
    """Build a rich Panel showing one blend's axis scores as bar charts."""
    geo = scores.get("geometric_total", 0)
    ratio_str = ":".join(str(r) for r in ratios)
    style_tag = scores.get("detected_style", "?")

    table = Table(show_header=False, box=None, padding=(0, 1), expand=True)
    table.add_column("Axis", style="bold", width=20)
    table.add_column("Bar", min_width=36)

    for ax in DISPLAY_AXES:
        v = scores.get(ax, 0)
        color = AXIS_COLORS.get(ax, "white")
        icon = AXIS_ICONS.get(ax, " ")
        label = f"{icon} {ax}"
        table.add_row(label, bar_chart(v, 30, color))

    title = f"[bold]{name}[/bold]  [dim]T:H:B = {ratio_str}[/dim]"
    subtitle = f"[bold {score_color(geo)}]Geo: {geo:.1f}[/]  │  Style: {style_tag}"

    return Panel(table, title=title, subtitle=subtitle,
                 border_style="bright_blue", expand=True)


def build_comparison_table(results: list[tuple[str, list[int], dict]]) -> Table:
    """Build a Rich table comparing all scored blends."""
    sorted_res = sorted(results, key=lambda x: x[2].get("geometric_total", 0), reverse=True)
    best_geo = sorted_res[0][2].get("geometric_total", 0) if sorted_res else 0

    table = Table(
        title="[bold bright_cyan]⚗  OPUS V — PYRAMID COMPARISON[/]",
        box=box.DOUBLE_EDGE,
        show_lines=True,
        header_style="bold bright_white on dark_blue",
        expand=True,
    )
    table.add_column("#", style="dim", width=3, justify="right")
    table.add_column("Blend", style="bold", min_width=24)
    table.add_column("T:H:B", justify="center", width=10)
    table.add_column("Geo", justify="right", width=7)

    for ax in DISPLAY_AXES:
        color = AXIS_COLORS.get(ax, "white")
        icon = AXIS_ICONS.get(ax, "")
        table.add_column(f"{icon}{ax[:6]}", justify="right", width=7, style=color)

    # Find per-axis bests for highlighting
    axis_bests = {}
    for ax in DISPLAY_AXES:
        best_val = max(r[2].get(ax, 0) for r in sorted_res)
        axis_bests[ax] = best_val

    for rank, (name, ratios, scores) in enumerate(sorted_res, 1):
        geo = scores.get("geometric_total", 0)
        ratio_str = ":".join(str(r) for r in ratios)

        geo_str = f"[bold bright_green]★ {geo:.1f}[/]" if geo == best_geo else f"{geo:.1f}"
        rank_str = f"[bold gold1]{rank}[/]" if rank <= 3 else str(rank)

        cells = [rank_str, name, ratio_str, geo_str]
        for ax in DISPLAY_AXES:
            v = scores.get(ax, 0)
            is_best = abs(v - axis_bests[ax]) < 0.05
            if is_best:
                cells.append(f"[bold underline]{v:.1f}[/]")
            else:
                cells.append(f"{v:.1f}")

        table.add_row(*cells)

    return table


def build_pyramid_panel() -> Panel:
    """Show the pyramid composition with material counts and percentages."""
    orig = compute_original_totals()
    grand = sum(orig)

    table = Table(box=box.SIMPLE_HEAVY, expand=True, show_edge=False)
    table.add_column("Layer", style="bold", width=8)
    table.add_column("Materials", justify="right", width=5)
    table.add_column("%", justify="right", width=6)
    table.add_column("Key Materials", ratio=1)

    layer_colors = ["bright_yellow", "bright_magenta", "bright_cyan"]
    layer_icons = ["🍋", "🌸", "🪵"]

    for i, (mname, mod) in enumerate(MODULES):
        pct = orig[i] / grand * 100
        top3 = sorted(mod.items(), key=lambda x: -x[1])[:4]
        top3_str = ", ".join(f"{m}" for m, _ in top3)
        table.add_row(
            f"[{layer_colors[i]}]{layer_icons[i]} {mname}[/]",
            str(len(mod)),
            f"{pct:.0f}%",
            f"[dim]{top3_str}[/dim]",
        )

    table.add_row("[bold]Total[/]", f"[bold]{sum(len(m) for _, m in MODULES)}[/]",
                  "100%", "")

    return Panel(table, title="[bold]🔺 Pyramid Composition[/]",
                 border_style="bright_blue", expand=True)


def build_module_detail(layer_name: str, module: dict) -> Table:
    """Detailed table of materials in a module."""
    table = Table(
        title=f"[bold]{layer_name.upper()}[/]",
        box=box.ROUNDED,
        show_lines=False,
        header_style="bold",
    )
    table.add_column("Material", style="bright_white", min_width=26)
    table.add_column("Parts", justify="right", width=8)
    table.add_column("%", justify="right", width=7)
    table.add_column("Dilution", justify="center", width=8)

    total = sum(module.values())
    for mat, parts in sorted(module.items(), key=lambda x: -x[1]):
        pct = parts / total * 100
        dil = DILUTIONS.get(mat)
        dil_str = f"[yellow]{int(dil*100)}%[/]" if dil else "[dim]neat[/]"
        table.add_row(mat, f"{parts:.2f}", f"{pct:.1f}%", dil_str)

    table.add_row("[bold]TOTAL[/]", f"[bold]{total:.2f}[/]", "100%", "")
    return table


def show_best_per_axis(results: list[tuple[str, list[int], dict]]):
    """Show which blend wins each axis."""
    table = Table(
        title="[bold bright_cyan]🏆 Best Per Axis[/]",
        box=box.SIMPLE_HEAVY,
        show_edge=False,
    )
    table.add_column("Axis", style="bold", width=22)
    table.add_column("Winner", min_width=24)
    table.add_column("Score", justify="right", width=7)

    for ax in DISPLAY_AXES:
        best = max(results, key=lambda x: x[2].get(ax, 0))
        v = best[2].get(ax, 0)
        color = AXIS_COLORS.get(ax, "white")
        icon = AXIS_ICONS.get(ax, "")
        table.add_row(
            f"[{color}]{icon} {ax}[/]",
            f"[bold]{best[0]}[/]",
            f"[{score_color(v)}]{v:.1f}[/]",
        )

    console.print(table)


# ─────────────────────────────────────────────────────────────────
# ACTIONS
# ─────────────────────────────────────────────────────────────────

def action_score_all():
    """Score all presets and show comparison."""
    console.print("\n[bold bright_cyan]Scoring all presets...[/]\n")
    results = []
    for name, ratios in PRESETS:
        with console.status(f"  Scoring [bold]{name}[/]..."):
            ingredients = blend_modules(ratios)
            scores = score_blend(ingredients, name)
            results.append((name, ratios, scores))
        geo = scores.get("geometric_total", 0)
        console.print(f"  [green]✓[/] {name:30s} → [bold]{geo:.1f}[/]")

    console.print()
    console.print(build_comparison_table(results))
    console.print()
    show_best_per_axis(results)
    return results


def action_score_one(presets_list=None):
    """Pick a preset or enter custom ratios, then show detailed breakdown."""
    source = presets_list or PRESETS

    console.print("\n[bold]Select a preset:[/]")
    for i, (name, ratios) in enumerate(source, 1):
        ratio_str = ":".join(str(r) for r in ratios)
        console.print(f"  [bright_cyan]{i:>2}[/]) {name:30s} [dim]{ratio_str}[/dim]")
    console.print(f"  [bright_cyan] 0[/]) Enter custom T:H:B ratio")

    choice = IntPrompt.ask("\nChoice", default=1)

    if choice == 0:
        t = IntPrompt.ask("  Top %", default=12)
        h = IntPrompt.ask("  Heart %", default=58)
        b = IntPrompt.ask("  Base %", default=30)
        ratios = [t, h, b]
        name = f"Custom ({t}:{h}:{b})"
    elif 1 <= choice <= len(source):
        name, ratios = source[choice - 1]
    else:
        console.print("[red]Invalid choice.[/]")
        return None

    with console.status(f"Scoring [bold]{name}[/]..."):
        ingredients = blend_modules(ratios)
        scores = score_blend(ingredients, name)

    console.print()
    console.print(build_axis_panel(name, ratios, scores))

    # Show the ingredient breakdown for this blend
    total_parts = sum(ingredients.values())
    table = Table(title=f"[bold]Ingredient Breakdown — {name}[/]",
                  box=box.ROUNDED, show_lines=False)
    table.add_column("#", width=3, justify="right", style="dim")
    table.add_column("Material", min_width=26)
    table.add_column("Layer", width=7, justify="center")
    table.add_column("Parts", justify="right", width=8)
    table.add_column("%", justify="right", width=7)

    # Tag each material with its layer
    layer_map = {}
    layer_styles = {"Top": "bright_yellow", "Heart": "bright_magenta", "Base": "bright_cyan"}
    for lname, mod in MODULES:
        for mat in mod:
            layer_map[mat] = lname

    for i, (mat, parts) in enumerate(sorted(ingredients.items(), key=lambda x: -x[1]), 1):
        pct = parts / total_parts * 100
        layer = layer_map.get(mat, "?")
        lstyle = layer_styles.get(layer, "white")
        table.add_row(str(i), mat, f"[{lstyle}]{layer}[/]",
                      f"{parts:.2f}", f"{pct:.1f}%")

    console.print(table)
    return (name, ratios, scores)


def action_compare_two(all_results=None):
    """Side-by-side comparison of two blends."""
    if not all_results or len(all_results) < 2:
        console.print("[yellow]Score all presets first (option 1).[/]")
        return

    console.print("\n[bold]Select two blends to compare:[/]")
    for i, (name, ratios, _) in enumerate(all_results, 1):
        ratio_str = ":".join(str(r) for r in ratios)
        console.print(f"  [bright_cyan]{i:>2}[/]) {name:30s} [dim]{ratio_str}[/dim]")

    a = IntPrompt.ask("First blend", default=1) - 1
    b = IntPrompt.ask("Second blend", default=2) - 1

    if not (0 <= a < len(all_results) and 0 <= b < len(all_results)):
        console.print("[red]Invalid selection.[/]")
        return

    na, ra, sa = all_results[a]
    nb, rb, sb = all_results[b]

    table = Table(
        title=f"[bold bright_cyan]⚖  {na}  vs  {nb}[/]",
        box=box.DOUBLE_EDGE, show_lines=True, expand=True,
    )
    table.add_column("Axis", style="bold", width=22)
    table.add_column(na, justify="center", min_width=14)
    table.add_column("", justify="center", width=3)  # delta arrow
    table.add_column(nb, justify="center", min_width=14)

    for ax in DISPLAY_AXES:
        va = sa.get(ax, 0)
        vb = sb.get(ax, 0)
        delta = va - vb
        icon = AXIS_ICONS.get(ax, "")
        color = AXIS_COLORS.get(ax, "white")

        if abs(delta) < 0.2:
            arrow = "[dim]=[/]"
        elif delta > 0:
            arrow = "[green]◀[/]"
        else:
            arrow = "[red]▶[/]"

        cell_a = f"[{score_color(va)}]{va:.1f}[/]"
        cell_b = f"[{score_color(vb)}]{vb:.1f}[/]"

        if delta > 0:
            cell_a = f"[bold underline]{va:.1f}[/]"
        elif delta < 0:
            cell_b = f"[bold underline]{vb:.1f}[/]"

        table.add_row(f"[{color}]{icon} {ax}[/]", cell_a, arrow, cell_b)

    # Geometric total row
    ga = sa.get("geometric_total", 0)
    gb = sb.get("geometric_total", 0)
    gd = ga - gb
    garrow = "[green]◀[/]" if gd > 0 else "[red]▶[/]" if gd < 0 else "[dim]=[/]"
    gcell_a = f"[bold {score_color(ga)}]{ga:.1f}[/]"
    gcell_b = f"[bold {score_color(gb)}]{gb:.1f}[/]"
    table.add_row("[bold gold1]★ GEOMETRIC[/]", gcell_a, garrow, gcell_b)

    console.print()
    console.print(table)


def action_show_pyramid():
    """Show the pyramid composition breakdown."""
    console.print()
    console.print(build_pyramid_panel())

    choice = Prompt.ask(
        "\nShow detail for [bright_yellow]T[/]op, [bright_magenta]H[/]eart, [bright_cyan]B[/]ase, or [dim]Enter[/] to skip",
        default=""
    )
    if choice.lower().startswith("t"):
        console.print(build_module_detail("Top", TOP))
    elif choice.lower().startswith("h"):
        console.print(build_module_detail("Heart", HEART))
    elif choice.lower().startswith("b"):
        console.print(build_module_detail("Base", BASE))
    elif choice.lower() == "a":
        for lname, mod in MODULES:
            console.print(build_module_detail(lname, mod))
            console.print()


def action_custom_ratio():
    """Quick custom ratio scorer."""
    console.print("\n[bold]Enter custom pyramid ratio:[/]")
    t = IntPrompt.ask("  Top %", default=12)
    h = IntPrompt.ask("  Heart %", default=58)
    b = IntPrompt.ask("  Base %", default=30)
    ratios = [t, h, b]
    name = f"Custom ({t}:{h}:{b})"

    with console.status(f"Scoring [bold]{name}[/]..."):
        ingredients = blend_modules(ratios)
        scores = score_blend(ingredients, name)

    console.print()
    console.print(build_axis_panel(name, ratios, scores))
    return (name, ratios, scores)


# ─────────────────────────────────────────────────────────────────
# FORMULA LIBRARY — Scan, classify T/H/B, score
# ─────────────────────────────────────────────────────────────────

@dataclass
class LoadedFormula:
    """A formula loaded from any source, with T/H/B analysis."""
    name: str
    source: str                      # filename or "accord_discovery"
    ingredients: dict[str, float]    # name → amount (µL or %)
    dilutions: dict[str, float]
    top_pct: float = 0.0
    heart_pct: float = 0.0
    base_pct: float = 0.0
    ingredient_count: int = 0
    scores: dict | None = None       # filled on demand


def _parse_dilution_factor(raw: str) -> float:
    """'10%' → 0.1, 'neat' → 1.0, '30% w/v' → 0.3"""
    raw = raw.strip().lower()
    if raw in ("", "neat", "pure", "—", "-", "premade accord"):
        return 1.0
    m = re.match(r"(\d+(?:\.\d+)?)\s*%", raw)
    return float(m.group(1)) / 100.0 if m else 1.0


def _parse_table_formula(text: str, name: str, source: str) -> LoadedFormula | None:
    """Parse a markdown table formula (| # | Ingredient | Dilution | µL | mL |)."""
    ingredients: dict[str, float] = {}
    dilutions: dict[str, float] = {}
    for line in text.split("\n"):
        if "**—" in line or "---" in line:
            continue
        m = re.match(
            r'\|\s*(\d+)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|',
            line,
        )
        if m:
            ing = m.group(2).strip().replace("**", "")
            if "ethanol" in ing.lower() or "total" in ing.lower():
                continue
            amount_ul = float(m.group(4))
            dilutions[ing] = _parse_dilution_factor(m.group(3))
            ingredients[ing] = amount_ul
    if not ingredients:
        return None
    return LoadedFormula(name=name, source=source, ingredients=ingredients,
                         dilutions=dilutions, ingredient_count=len(ingredients))


def _classify_formula_thb(formula: LoadedFormula):
    """Fill top_pct / heart_pct / base_pct using classify_note()."""
    totals = {"top": 0.0, "heart": 0.0, "base": 0.0}
    for mat, amt in formula.ingredients.items():
        note = classify_note(mat)
        totals[note] += amt
    grand = sum(totals.values())
    if grand > 0:
        formula.top_pct = totals["top"] / grand * 100
        formula.heart_pct = totals["heart"] / grand * 100
        formula.base_pct = totals["base"] / grand * 100


def scan_all_formulas() -> list[LoadedFormula]:
    """Scan workspace for all parseable formulas and accords."""
    formulas: list[LoadedFormula] = []

    # ── 1. Luxury formulas (## N. Name pattern) ──
    lux_path = PROJECT_ROOT / "luxury_formulas_2026-03-26.md"
    if lux_path.exists():
        try:
            for info in parse_formulas(lux_path):
                lf = LoadedFormula(
                    name=info.name, source=lux_path.name,
                    ingredients=dict(info.ingredients),
                    dilutions=dict(info.dilutions),
                    ingredient_count=len(info.ingredients),
                )
                formulas.append(lf)
        except Exception:
            pass

    # ── 2. Optimized luxury formulas ──
    opt_path = PROJECT_ROOT / "luxury_formulas_optimized.md"
    if opt_path.exists():
        try:
            for info in parse_formulas(opt_path):
                lf = LoadedFormula(
                    name=f"{info.name} (opt)", source=opt_path.name,
                    ingredients=dict(info.ingredients),
                    dilutions=dict(info.dilutions),
                    ingredient_count=len(info.ingredients),
                )
                formulas.append(lf)
        except Exception:
            pass

    # ── 3. Individual .md formula files (Mixing Guides, Optimized, etc.) ──
    seen_names = {f.name for f in formulas}
    for md_path in sorted(PROJECT_ROOT.glob("*.md")):
        if md_path.name.startswith("_") or md_path.name in (lux_path.name, opt_path.name if opt_path.exists() else ""):
            continue
        if md_path.name in ("inventory.txt", "shopping_list.md", "fragrance_families_reference.md",
                            "expansion_recommendations.md", "README.md"):
            continue
        try:
            text = md_path.read_text(encoding="utf-8")
        except Exception:
            continue
        # Try the ## N. Name pattern first
        sections = re.split(r'^## (\d+)\.\s+(.+?)$', text, flags=re.MULTILINE)
        if len(sections) >= 4:
            for i in range(1, len(sections) - 2, 3):
                name = sections[i + 1].strip()
                body = sections[i + 2]
                if name not in seen_names:
                    lf = _parse_table_formula(body, name, md_path.name)
                    if lf:
                        seen_names.add(name)
                        formulas.append(lf)
        else:
            # Single-formula file — extract name from # title
            title_m = re.match(r'^#\s+(.+?)(?:\s*[-—]|$)', text, re.MULTILINE)
            fname = title_m.group(1).strip() if title_m else md_path.stem.replace("_", " ")
            if fname not in seen_names:
                lf = _parse_table_formula(text, fname, md_path.name)
                if lf:
                    seen_names.add(fname)
                    formulas.append(lf)

    # ── 4. Accord discovery results ──
    accord_path = PROJECT_ROOT / "accord_discovery_results.json"
    if accord_path.exists():
        try:
            accords = json.loads(accord_path.read_text(encoding="utf-8"))
            for acc in accords:
                name = acc.get("accord", "Unknown Accord")
                ings = acc.get("ingredients", {})
                if ings and name not in seen_names:
                    lf = LoadedFormula(
                        name=name, source="accord_discovery",
                        ingredients={k: v for k, v in ings.items()},
                        dilutions={},
                        ingredient_count=len(ings),
                    )
                    seen_names.add(name)
                    formulas.append(lf)
        except Exception:
            pass

    # ── 5. DHI reverse engineering results ──
    dhi_path = PROJECT_ROOT / "dhi_reverse_engineering_results.json"
    if dhi_path.exists():
        try:
            dhi_list = json.loads(dhi_path.read_text(encoding="utf-8"))
            for entry in dhi_list:
                name = entry.get("name", "DHI Variant")
                ings = entry.get("ingredients", {})
                if ings and name not in seen_names:
                    lf = LoadedFormula(
                        name=name, source="dhi_reverse_eng",
                        ingredients={k: v for k, v in ings.items()},
                        dilutions={},
                        ingredient_count=len(ings),
                    )
                    seen_names.add(name)
                    formulas.append(lf)
        except Exception:
            pass

    # Classify T/H/B for all formulas
    for f in formulas:
        _classify_formula_thb(f)

    return formulas


def _score_loaded_formula(lf: LoadedFormula) -> dict:
    """Score a LoadedFormula through the 10-axis pipeline."""
    total = sum(lf.ingredients.values())
    if total == 0:
        return {}
    pct_dict = {name: (amt / total) * 100 for name, amt in lf.ingredients.items()}
    fv = FormulaVector(ingredients=pct_dict, dilutions=dict(lf.dilutions))
    sg = SynergyGraph()
    sg.build(fv)
    scorer = FormulaScorer(synergy_graph=sg)
    return scorer.score(fv)


# ── Formula Browser Display ──

def build_formula_library_table(formulas: list[LoadedFormula],
                                 sort_by: str = "name") -> Table:
    """Build a table of all formulas with T:H:B breakdown."""
    if sort_by == "top":
        formulas = sorted(formulas, key=lambda f: -f.top_pct)
    elif sort_by == "heart":
        formulas = sorted(formulas, key=lambda f: -f.heart_pct)
    elif sort_by == "base":
        formulas = sorted(formulas, key=lambda f: -f.base_pct)
    elif sort_by == "score":
        formulas = sorted(formulas, key=lambda f: -(f.scores or {}).get("geometric_total", 0))
    else:
        formulas = sorted(formulas, key=lambda f: f.name.lower())

    table = Table(
        title="[bold bright_cyan]⚗  FORMULA LIBRARY — T / H / B Analysis[/]",
        box=box.DOUBLE_EDGE, show_lines=False,
        header_style="bold bright_white on dark_blue",
        expand=True,
    )
    table.add_column("#", width=3, justify="right", style="dim")
    table.add_column("Formula", min_width=34)
    table.add_column("Source", width=16, style="dim")
    table.add_column("Mats", width=4, justify="right")
    table.add_column("Top%", width=6, justify="right", style="bright_yellow")
    table.add_column("Heart%", width=7, justify="right", style="bright_magenta")
    table.add_column("Base%", width=6, justify="right", style="bright_cyan")
    table.add_column("Ratio", width=12, justify="center")
    table.add_column("Geo", width=6, justify="right")

    for i, f in enumerate(formulas, 1):
        # Build a compact ratio like 12:58:30
        t_r = round(f.top_pct)
        h_r = round(f.heart_pct)
        b_r = round(f.base_pct)
        ratio_str = f"{t_r}:{h_r}:{b_r}"

        # Colour-code the ratio by balance
        if t_r < 5:
            ratio_style = "dark_orange"     # very top-light
        elif b_r > 60:
            ratio_style = "bright_cyan"     # base-heavy
        elif abs(h_r - 50) < 15:
            ratio_style = "green"           # balanced
        else:
            ratio_style = "yellow"

        geo = ""
        if f.scores:
            g = f.scores.get("geometric_total", 0)
            geo = f"[{score_color(g)}]{g:.1f}[/]"

        src_short = f.source[:15] if len(f.source) > 15 else f.source
        table.add_row(
            str(i), f.name, src_short, str(f.ingredient_count),
            f"{f.top_pct:.1f}", f"{f.heart_pct:.1f}", f"{f.base_pct:.1f}",
            f"[{ratio_style}]{ratio_str}[/]", geo,
        )

    return table


def action_formula_library():
    """Browse all formulas with T/H/B classification, then select to score."""
    console.print("\n[bold bright_cyan]Scanning workspace for formulas...[/]")
    formulas = scan_all_formulas()
    console.print(f"  Found [bold]{len(formulas)}[/] formulas/accords.\n")

    if not formulas:
        console.print("[yellow]No formulas found.[/]")
        return None

    sort_by = "name"
    scored_all = False

    while True:
        console.print(build_formula_library_table(formulas, sort_by=sort_by))

        console.print(f"\n  [dim]Sorted by: {sort_by}[/]")
        console.print("  [bright_cyan]N[/]=select by #   "
                       "[bright_cyan]S[/]=score all   "
                       "[bright_cyan]T[/]/[bright_cyan]H[/]/[bright_cyan]B[/]=sort by layer   "
                       "[bright_cyan]G[/]=sort by score   "
                       "[bright_cyan]A[/]=sort by name   "
                       "[bright_cyan]C[/]=compare two   "
                       "[dim]Enter[/]=back")

        choice = Prompt.ask("\n[bold]Choice[/]", default="")

        if choice == "":
            break
        elif choice.lower() == "s":
            # Score all formulas
            console.print("\n[bold]Scoring all formulas...[/]")
            for i, f in enumerate(formulas):
                with console.status(f"  Scoring [bold]{f.name}[/] ({i+1}/{len(formulas)})..."):
                    try:
                        f.scores = _score_loaded_formula(f)
                    except Exception as e:
                        f.scores = {"geometric_total": 0, "_error": str(e)}
                geo = (f.scores or {}).get("geometric_total", 0)
                console.print(f"  [green]✓[/] {f.name:40s} → [bold]{geo:.1f}[/]")
            scored_all = True
            sort_by = "score"  # auto-switch to score sort after scoring
        elif choice.lower() == "t":
            sort_by = "top"
        elif choice.lower() == "h":
            sort_by = "heart"
        elif choice.lower() == "b":
            sort_by = "base"
        elif choice.lower() == "g":
            sort_by = "score"
        elif choice.lower() == "a":
            sort_by = "name"
        elif choice.lower() == "c":
            # Compare two formulas
            a_idx = IntPrompt.ask("  First formula #", default=1) - 1
            b_idx = IntPrompt.ask("  Second formula #", default=2) - 1
            # Get the formulas in current sort order
            if sort_by == "top":
                sorted_formulas = sorted(formulas, key=lambda f: -f.top_pct)
            elif sort_by == "heart":
                sorted_formulas = sorted(formulas, key=lambda f: -f.heart_pct)
            elif sort_by == "base":
                sorted_formulas = sorted(formulas, key=lambda f: -f.base_pct)
            elif sort_by == "score":
                sorted_formulas = sorted(formulas, key=lambda f: -(f.scores or {}).get("geometric_total", 0))
            else:
                sorted_formulas = sorted(formulas, key=lambda f: f.name.lower())

            if 0 <= a_idx < len(sorted_formulas) and 0 <= b_idx < len(sorted_formulas):
                fa = sorted_formulas[a_idx]
                fb = sorted_formulas[b_idx]
                # Score if needed
                for ff in (fa, fb):
                    if not ff.scores:
                        with console.status(f"  Scoring [bold]{ff.name}[/]..."):
                            try:
                                ff.scores = _score_loaded_formula(ff)
                            except Exception as e:
                                ff.scores = {"geometric_total": 0}
                _show_formula_comparison(fa, fb)
            else:
                console.print("[red]Invalid selection.[/]")
        elif choice.lower() == "n" or choice.isdigit():
            # Select a formula by number
            if choice.lower() == "n":
                idx = IntPrompt.ask("  Formula #", default=1) - 1
            else:
                idx = int(choice) - 1
            # Get in current sort order
            if sort_by == "top":
                sorted_formulas = sorted(formulas, key=lambda f: -f.top_pct)
            elif sort_by == "heart":
                sorted_formulas = sorted(formulas, key=lambda f: -f.heart_pct)
            elif sort_by == "base":
                sorted_formulas = sorted(formulas, key=lambda f: -f.base_pct)
            elif sort_by == "score":
                sorted_formulas = sorted(formulas, key=lambda f: -(f.scores or {}).get("geometric_total", 0))
            else:
                sorted_formulas = sorted(formulas, key=lambda f: f.name.lower())

            if 0 <= idx < len(sorted_formulas):
                _show_formula_detail(sorted_formulas[idx])
            else:
                console.print("[red]Invalid number.[/]")

    return formulas


def _get_sorted_formulas(formulas, sort_by):
    if sort_by == "top":
        return sorted(formulas, key=lambda f: -f.top_pct)
    elif sort_by == "heart":
        return sorted(formulas, key=lambda f: -f.heart_pct)
    elif sort_by == "base":
        return sorted(formulas, key=lambda f: -f.base_pct)
    elif sort_by == "score":
        return sorted(formulas, key=lambda f: -(f.scores or {}).get("geometric_total", 0))
    return sorted(formulas, key=lambda f: f.name.lower())


def _show_formula_detail(f: LoadedFormula):
    """Show full detail for one formula — ingredients by T/H/B, then scoring."""
    # Score if not yet scored
    if not f.scores:
        with console.status(f"Scoring [bold]{f.name}[/]..."):
            try:
                f.scores = _score_loaded_formula(f)
            except Exception as e:
                f.scores = {"geometric_total": 0, "_error": str(e)}

    geo = (f.scores or {}).get("geometric_total", 0)
    ratio_str = f"{round(f.top_pct)}:{round(f.heart_pct)}:{round(f.base_pct)}"

    # Axis bar chart panel
    table = Table(show_header=False, box=None, padding=(0, 1), expand=True)
    table.add_column("Axis", style="bold", width=20)
    table.add_column("Bar", min_width=36)
    for ax in DISPLAY_AXES:
        v = (f.scores or {}).get(ax, 0)
        color = AXIS_COLORS.get(ax, "white")
        icon = AXIS_ICONS.get(ax, " ")
        table.add_row(f"{icon} {ax}", bar_chart(v, 30, color))

    panel = Panel(
        table,
        title=f"[bold]{f.name}[/]  [dim]T:H:B = {ratio_str}[/dim]  [dim]({f.source})[/dim]",
        subtitle=f"[bold {score_color(geo)}]Geo: {geo:.1f}[/]",
        border_style="bright_blue", expand=True,
    )
    console.print()
    console.print(panel)

    # Ingredient table grouped by T/H/B
    layer_styles = {"top": "bright_yellow", "heart": "bright_magenta", "base": "bright_cyan"}
    layer_icons = {"top": "🍋", "heart": "🌸", "base": "🪵"}

    grouped: dict[str, list[tuple[str, float]]] = {"top": [], "heart": [], "base": []}
    for mat, amt in f.ingredients.items():
        note = classify_note(mat)
        grouped[note].append((mat, amt))

    total = sum(f.ingredients.values())
    itbl = Table(title=f"[bold]Ingredients by Pyramid Layer[/]",
                 box=box.ROUNDED, show_lines=False, expand=True)
    itbl.add_column("#", width=3, justify="right", style="dim")
    itbl.add_column("Material", min_width=28)
    itbl.add_column("Layer", width=7, justify="center")
    itbl.add_column("Amount", justify="right", width=9)
    itbl.add_column("%", justify="right", width=6)

    row_num = 0
    for layer in ("top", "heart", "base"):
        items = sorted(grouped[layer], key=lambda x: -x[1])
        for mat, amt in items:
            row_num += 1
            pct = amt / total * 100 if total > 0 else 0
            lstyle = layer_styles[layer]
            icon = layer_icons[layer]
            itbl.add_row(str(row_num), mat,
                         f"[{lstyle}]{icon} {layer.title()}[/]",
                         f"{amt:.1f}", f"{pct:.1f}%")

    console.print(itbl)

    # Pyramid bar visualization
    console.print()
    _print_pyramid_bar(f)


def _print_pyramid_bar(f: LoadedFormula):
    """Print a horizontal stacked bar showing T/H/B split."""
    width = 50
    t_w = max(1, int(f.top_pct / 100 * width))
    h_w = max(1, int(f.heart_pct / 100 * width))
    b_w = width - t_w - h_w

    t = Text()
    t.append(f"  T {f.top_pct:4.1f}% ", style="bold bright_yellow")
    t.append("█" * t_w, style="bright_yellow")
    t.append("█" * h_w, style="bright_magenta")
    t.append("█" * b_w, style="bright_cyan")
    t.append(f" {f.base_pct:4.1f}% B", style="bold bright_cyan")
    console.print(t)
    t2 = Text()
    t2.append(f"         {'':>{t_w}}")
    t2.append(f"H {f.heart_pct:.1f}%", style="bold bright_magenta")
    console.print(t2)


def _show_formula_comparison(fa: LoadedFormula, fb: LoadedFormula):
    """Side-by-side comparison of two loaded formulas."""
    table = Table(
        title=f"[bold bright_cyan]⚖  {fa.name}  vs  {fb.name}[/]",
        box=box.DOUBLE_EDGE, show_lines=True, expand=True,
    )
    table.add_column("Axis", style="bold", width=22)
    table.add_column(fa.name[:24], justify="center", min_width=12)
    table.add_column("", justify="center", width=3)
    table.add_column(fb.name[:24], justify="center", min_width=12)

    sa = fa.scores or {}
    sb = fb.scores or {}

    for ax in DISPLAY_AXES:
        va = sa.get(ax, 0)
        vb = sb.get(ax, 0)
        delta = va - vb
        color = AXIS_COLORS.get(ax, "white")
        icon = AXIS_ICONS.get(ax, "")

        if abs(delta) < 0.2:
            arrow = "[dim]=[/]"
        elif delta > 0:
            arrow = "[green]◀[/]"
        else:
            arrow = "[red]▶[/]"

        cell_a = f"[{score_color(va)}]{va:.1f}[/]"
        cell_b = f"[{score_color(vb)}]{vb:.1f}[/]"
        if delta > 0.2:
            cell_a = f"[bold underline]{va:.1f}[/]"
        elif delta < -0.2:
            cell_b = f"[bold underline]{vb:.1f}[/]"

        table.add_row(f"[{color}]{icon} {ax}[/]", cell_a, arrow, cell_b)

    # Geometric
    ga = sa.get("geometric_total", 0)
    gb = sb.get("geometric_total", 0)
    gd = ga - gb
    garrow = "[green]◀[/]" if gd > 0.2 else "[red]▶[/]" if gd < -0.2 else "[dim]=[/]"
    table.add_row("[bold gold1]★ GEOMETRIC[/]",
                  f"[bold {score_color(ga)}]{ga:.1f}[/]", garrow,
                  f"[bold {score_color(gb)}]{gb:.1f}[/]")

    # Pyramid ratios
    table.add_row("[bold]T:H:B[/]",
                  f"{round(fa.top_pct)}:{round(fa.heart_pct)}:{round(fa.base_pct)}",
                  "",
                  f"{round(fb.top_pct)}:{round(fb.heart_pct)}:{round(fb.base_pct)}")

    console.print()
    console.print(table)


# ─────────────────────────────────────────────────────────────────
# MAIN MENU
# ─────────────────────────────────────────────────────────────────

BANNER = r"""
[bright_cyan]
   ╔═══════════════════════════════════════════════════════╗
   ║   ⚗  OPUS V — IRIS PYRAMID SCORER                   ║
   ║   Top / Heart / Base  ·  10-Axis Pipeline            ║
   ╚═══════════════════════════════════════════════════════╝
[/]"""


def main():
    console.print(BANNER)

    all_results = None

    while True:
        console.print("\n[bold bright_white on dark_blue]  MENU  [/]")
        console.print("  [bright_cyan]1[/]) Score all presets (comparison table)")
        console.print("  [bright_cyan]2[/]) Score single preset (detailed view)")
        console.print("  [bright_cyan]3[/]) Quick custom T:H:B ratio")
        console.print("  [bright_cyan]4[/]) Compare two blends side-by-side")
        console.print("  [bright_cyan]5[/]) Show pyramid composition")
        console.print("  [bright_cyan]6[/]) Export last results to CSV")
        console.print("  [bright_cyan]7[/]) [bold]Formula Library[/] — browse all formulas by T/H/B")
        console.print("  [bright_cyan]q[/]) Quit")

        choice = Prompt.ask("\n[bold]Choice[/]", default="1")

        if choice == "1":
            all_results = action_score_all()
        elif choice == "2":
            result = action_score_one()
            if result and all_results is None:
                all_results = [result]
            elif result:
                all_results.append(result)
        elif choice == "3":
            result = action_custom_ratio()
            if result and all_results is None:
                all_results = [result]
            elif result:
                all_results.append(result)
        elif choice == "4":
            action_compare_two(all_results)
        elif choice == "5":
            action_show_pyramid()
        elif choice == "6":
            if all_results:
                from opus_v_thb_scorer import export_csv
                export_csv(all_results)
                console.print("[green]✓ Exported to opus_v_thb_comparison.csv[/]")
            else:
                console.print("[yellow]No results to export yet. Score presets first.[/]")
        elif choice == "7":
            action_formula_library()
        elif choice.lower() == "q":
            console.print("\n[dim]Goodbye.[/]")
            break
        else:
            console.print("[red]Invalid choice.[/]")


if __name__ == "__main__":
    main()
