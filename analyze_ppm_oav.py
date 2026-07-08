"""Instant PPM / ODT / OAV analysis for any perfume formula.

Drop a formula markdown file and get a terminal table + JSON/CSV output
with concentration (ppm), odor detection threshold, and odor activity value
for every material.

Usage:
    python analyze_ppm_oav.py formulas/My_Formula_30mL.md
    python analyze_ppm_oav.py formulas/My_Formula_30mL.md --batch-ml 50
    python analyze_ppm_oav.py formulas/My_Formula_30mL.md --json-only

The formula markdown must have a table with columns Material / Dilution / uL
(or equivalents).  Same format as all existing formulas/.

Parsers:
    | Material | Dilution | uL |
    | Material | Dilution | uL | (with extra columns ignored)
    | # | Material | Dilution | uL |

If you have a collection (multi-formula file), each ## heading starts a
new formula.  All are analysed independently.

Output:
    - Terminal table with OAV bands colour-coded
    - _{stem}_ppm_oav.json — machine-readable audit data
    - _{stem}_ppm_oav.csv — spreadsheet-friendly export
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from engine.ingredient_intelligence import get_profile
from engine.name_utils import normalize_name
from engine.optimizer.oav_guard import _lookup_odt


# ── data structures ──────────────────────────────────────────────────────────

@dataclass
class MaterialRow:
    material: str
    dilution_pct: float
    stock_ul: float
    active_ul: float
    active_ppm_finished: float
    active_pct_finished: float
    odt_ppm: float | None
    oav: float | None
    oav_band: str


@dataclass
class FormulaSpec:
    index: int
    title: str
    rows: list[MaterialRow]


# ── ODT lookup ───────────────────────────────────────────────────────────────

def _odt_ppm(material: str) -> float | None:
    odt = _lookup_odt(normalize_name(material))
    if odt is not None:
        return odt
    profile = get_profile(material)
    return getattr(profile, "odt_ppm", None) if profile else None


# ── OAV banding ──────────────────────────────────────────────────────────────

def _band(oav: float | None) -> str:
    if oav is None:
        return "no_odt"
    if oav < 0.1:
        return "silent"
    if oav < 1.0:
        return "shadow"
    if oav < 3.0:
        return "threshold"
    if oav < 30.0:
        return "active"
    if oav < 300.0:
        return "strong"
    return "dominant"


# ── colour / console helpers ─────────────────────────────────────────────────

_COLORS: dict[str, str] = {
    "silent":    "\033[90m",   # grey
    "shadow":    "\033[37m",   # white
    "threshold": "\033[36m",   # cyan
    "active":    "\033[32m",   # green
    "strong":    "\033[33m",   # yellow
    "dominant":  "\033[31m",   # red
    "no_odt":    "\033[35m",   # magenta
    "reset":     "\033[0m",
}

# fallback to empty strings if stdout is not a tty
if not sys.stdout.isatty():
    _COLORS = {k: "" for k in _COLORS}


def _color_band(band: str) -> str:
    return _COLORS.get(band, "")


def _color_text(text: str, band: str) -> str:
    return f"{_color_band(band)}{text}{_COLORS['reset']}"


# ── formula parser ───────────────────────────────────────────────────────────

def _parse_formula_md(path: Path, prefer_ml: float | None = None) -> list[dict[str, Any]]:
    """Parse a markdown file into one or more formula dicts.

    Each formula dict has: index, title, ingredients_ul {name: uL},
    dilutions {name: fraction}, total_ul (sum of stock uL).

    Single-formula files (one # or ## heading): all tables merged into one formula.
    Multi-formula collection files (multiple ##): each ## heading = one formula.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="cp1252")

    # Detect if this is a collection: multiple ## headings that look like
    # numbered formula entries (e.g. "## 1. FORMULA NAME")
    collection_headings = re.findall(r"^##\s+\d+\..*$", text, re.MULTILINE)
    is_collection = len(collection_headings) >= 2

    formulas: list[dict[str, Any]] = []

    if is_collection:
        # Multi-formula: each ## heading is a separate formula
        h2_sections = re.split(r"\n(?=##\s)", text)
        for idx, sec in enumerate(h2_sections, start=1):
            title_match = re.match(r"##\s*(.+?)(?:\s*\{|$)", sec.strip())
            title = title_match.group(1).strip() if title_match else path.stem
            ing, dil = _extract_tables(sec, prefer_ml)
            if ing:
                formulas.append({
                    "index": idx, "title": title,
                    "ingredients_ul": ing, "dilutions": dil,
                    "total_ul": sum(ing.values()),
                })
    else:
        # Single formula: extract all tables from the whole file
        title = path.stem
        h1_match = re.match(r"#\s*(.+?)(?:\n|$)", text.strip())
        if h1_match:
            title = h1_match.group(1).strip()
        ing, dil = _extract_tables(text, prefer_ml)
        if ing:
            formulas.append({
                "index": 1, "title": title,
                "ingredients_ul": ing, "dilutions": dil,
                "total_ul": sum(ing.values()),
            })

    return formulas


def _pick_ul_column(header_cells: list[str], ul_columns: list[int],
                    prefer_ml: float | None = None) -> int:
    """Pick the best µL column from a table header.

    Priority: batch-matched > any batch column > first µL column.
    """
    if len(ul_columns) == 1:
        return ul_columns[0]
    if prefer_ml is not None:
        prefer_str = f"{prefer_ml:g}ml"
        for idx in ul_columns:
            if prefer_str in header_cells[idx]:
                return idx
    for idx in ul_columns:
        if "batch" in header_cells[idx]:
            return idx
    return ul_columns[0]


def _extract_tables(text: str, prefer_ml: float | None = None) -> tuple[dict[str, float], dict[str, float]]:
    """Extract all material rows from all markdown tables in text.

    Returns (ingredients_ul, dilutions) — merged across all tables.
    Subsequent appearances of the same material overwrite earlier ones.
    """
    ingredients: dict[str, float] = {}
    dilutions: dict[str, float] = {}

    # Find all tables: lines that start with | and have at least 2 pipe-delimited cells
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line.startswith("|") or "---|---" in line:
            i += 1
            continue

        # This line is a potential table header — check that the next line is a separator
        i += 1
        if i >= len(lines):
            break
        sep_line = lines[i].strip()
        if not re.match(r"^\|[\s\-:]+\|[\s\-:]+\|", sep_line):
            i += 1
            continue

        # Parse header
        header_cells = [c.strip().lower() for c in line.split("|")[1:-1]]

        # Only parse tables that have uL/µL column (skip IFRA, architecture, etc.)
        ul_columns = [i for i, c in enumerate(header_cells)
                      if any(unit in c for unit in ("µl", "μl", "ul"))]
        has_ul_col = bool(ul_columns)
        if not has_ul_col:
            i += 1
            continue

        material_idx = next((i for i, c in enumerate(header_cells)
                             if c in ("material", "ingredient", "name", "chemical")), 0)
        dilution_idx = next((i for i, c in enumerate(header_cells)
                              if c in ("dilution", "dilution %", "dil %", "conc", "form")), -1)
        # Skip analysis/derived tables that lack a proper dilution column
        if dilution_idx < 0:
            i += 1
            continue
        ul_idx = _pick_ul_column(header_cells, ul_columns, prefer_ml)
        step_idx = next((i for i, c in enumerate(header_cells)
                          if c in ("#", "step", "no", "n")), None)

        # Parse data rows
        i += 1
        while i < len(lines):
            data_line = lines[i].strip()
            if not data_line.startswith("|"):
                break
            if re.match(r"^\|[\s\-:]+\|[\s\-:]+\|", data_line):
                i += 1
                continue

            cells = [c.strip() for c in data_line.split("|")[1:-1]]
            if step_idx is not None and step_idx < len(cells):
                try:
                    _ = int(cells[step_idx]) if cells[step_idx] else None
                except ValueError:
                    i += 1
                    continue

            if material_idx >= len(cells) or not cells[material_idx]:
                i += 1
                continue

            name = cells[material_idx].strip()

            # Skip subtotal/summary/header rows
            if name.lower() in ("", "subtotal", "total", "stage", "batch"):
                i += 1
                continue
            if any(kw in name.lower() for kw in ("subtotal", "stage", "batch")):
                i += 1
                continue
            if name.startswith("**") and name.endswith("**"):
                i += 1
                continue

            # Parse dilution
            dil_str = cells[dilution_idx].strip().lower() if dilution_idx < len(cells) else "neat"
            # Strip markdown formatting (bold **, italic *, __) before parsing
            dil_str = dil_str.replace("**", "").replace("__", "").replace("*", "")
            dil_str = dil_str.replace(" in ", " ").replace(" w/v", "").replace(" v/v", "")
            dil_str = dil_str.replace(" dpg", "").replace(" dep", "").replace(" tec", "").replace(" ipm", "")
            dil_str = dil_str.replace("etoh", "").replace("ethanol", "").strip()
            if dil_str in ("neat", "pure", "100%", "100", "nat"):
                dil = 1.0
            else:
                pct_match = re.match(r"(\d+\.?\d*)\s*%?", dil_str)
                dil = float(pct_match.group(1)) / 100.0 if pct_match else 1.0

            # Parse uL dose (strip spaces, commas, non-breaking spaces)
            try:
                ul_val = float(cells[ul_idx].replace(",", "").replace(" ", "").replace("\xa0", ""))
            except (IndexError, ValueError):
                i += 1
                continue

            ingredients[name] = ul_val
            dilutions[name] = dil
            i += 1

    return ingredients, dilutions


# ── analysis ─────────────────────────────────────────────────────────────────

def analyze(formulas: list[dict[str, Any]], batch_ml: float) -> list[FormulaSpec]:
    """Run PPM / ODT / OAV analysis on each parsed formula."""
    results: list[FormulaSpec] = []
    finished_ul = batch_ml * 1000.0

    for formula in formulas:
        rows: list[MaterialRow] = []
        for material, stock_ul in formula["ingredients_ul"].items():
            dilution = formula["dilutions"].get(material, 1.0)
            active_ul = stock_ul * dilution
            ppm = active_ul / finished_ul * 1_000_000.0 if finished_ul > 0 else 0.0
            odt = _odt_ppm(material)
            oav = ppm / odt if odt and odt > 0 else None

            rows.append(MaterialRow(
                material=material,
                dilution_pct=round(dilution * 100.0, 4),
                stock_ul=round(stock_ul, 4),
                active_ul=round(active_ul, 4),
                active_ppm_finished=round(ppm, 4),
                active_pct_finished=round(active_ul / finished_ul * 100.0, 6),
                odt_ppm=round(odt, 6) if odt is not None else None,
                oav=round(oav, 4) if oav is not None else None,
                oav_band=_band(oav),
            ))

        rows.sort(key=lambda r: (r.oav is None, -(r.oav or 0.0)))
        results.append(FormulaSpec(index=formula["index"], title=formula["title"], rows=rows))

    return results


# ── terminal output ──────────────────────────────────────────────────────────

def print_terminal(results: list[FormulaSpec], batch_ml: float) -> None:
    """Colour-coded terminal table."""
    print()
    print(f"{'=' * 100}")
    print(f"  PPM / ODT / OAV ANALYSIS  —  batch basis: {batch_ml:g} mL finished product")
    print(f"{'=' * 100}")

    for formula in results:
        if not formula.rows:
            continue
        cov = sum(1 for r in formula.rows if r.odt_ppm is not None)
        no_odt = len(formula.rows) - cov
        dominant = sum(1 for r in formula.rows if r.oav is not None and r.oav >= 300)
        max_oav = max((r.oav or 0.0 for r in formula.rows), default=0.0)

        print()
        print(f"  {formula.index}. {formula.title}  "
              f"[{len(formula.rows)} materials, {cov} ODT-covered, max OAV {max_oav:.1f}]")
        if no_odt:
            missing = [r.material for r in formula.rows if r.odt_ppm is None]
            print(f"  !! {no_odt} material(s) without ODT data: {', '.join(missing)}")
        print()

        # column widths
        w_mat = max(len(r.material) for r in formula.rows) + 2
        w_mat = min(w_mat, 50)

        print(f"  {'Material':<{w_mat}} {'Dil%':>6} {'Stock µL':>9} {'Active µL':>9} "
              f"{'ppm fin':>9} {'ODT ppm':>9} {'OAV':>9}  Band")
        print(f"  {'-' * w_mat} {'-' * 6} {'-' * 9} {'-' * 9} "
              f"{'-' * 9} {'-' * 9} {'-' * 9}  ----")

        for r in formula.rows:
            mat = r.material[:w_mat - 1]
            oav_str = f"{r.oav:,.1f}" if r.oav is not None else "-"
            odt_str = f"{r.odt_ppm:,.4f}" if r.odt_ppm is not None else "-"
            band_label = r.oav_band.replace("_", " ")

            print(_color_text(
                f"  {mat:<{w_mat}} {r.dilution_pct:>5.1f}% {r.stock_ul:>9,.1f} "
                f"{r.active_ul:>9,.3f} {r.active_ppm_finished:>9,.2f} "
                f"{odt_str:>9} {oav_str:>9}  {band_label}",
                r.oav_band,
            ))

        print()

    # legend
    print(f"  {_color_text('silent <0.1x', 'silent')}  "
          f"{_color_text('shadow 0.1-1x', 'shadow')}  "
          f"{_color_text('threshold 1-3x', 'threshold')}  "
          f"{_color_text('active 3-30x', 'active')}  "
          f"{_color_text('strong 30-300x', 'strong')}  "
          f"{_color_text('dominant >300x', 'dominant')}  "
          f"{_color_text('no ODT data', 'no_odt')}")
    print()
    print(f"  OAV = ppm(finished product) / ODT(ethanol, ppm)")
    print(f"  ODT source: engine.odor_thresholds with ingredient_intelligence fallback")
    print()


# ── file output ──────────────────────────────────────────────────────────────

def write_json(path: Path, results: list[FormulaSpec]) -> None:
    data = []
    for formula in results:
        for r in formula.rows:
            data.append({
                "formula_index": formula.index,
                "formula_title": formula.title,
                **asdict(r),
            })
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def write_csv(path: Path, results: list[FormulaSpec]) -> None:
    all_rows = [asdict(r) for f in results for r in f.rows]
    if not all_rows:
        return
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(all_rows[0].keys()))
        writer.writeheader()
        writer.writerows(all_rows)


def output_stem(path: Path) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", path.stem).strip("_").lower() + "_ppm_oav"


# ── CLI ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Instant PPM / ODT / OAV analysis for perfume formulas.")
    parser.add_argument("formula", type=Path, help="Path to formula markdown file")
    parser.add_argument("--batch-ml", type=float, default=30.0,
                        help="Finished product volume in mL (default: 30)")
    parser.add_argument("--json-only", action="store_true",
                        help="Skip terminal output, write only JSON+CSV")
    parser.add_argument("--csv-only", action="store_true",
                        help="Skip terminal output, write only CSV")
    parser.add_argument("-o", "--output-stem", type=str, default=None,
                        help="Override output file stem")
    args = parser.parse_args()

    path = args.formula if args.formula.is_absolute() else ROOT / args.formula
    if not path.exists():
        print(f"Error: file not found: {path}", file=sys.stderr)
        return 1

    formulas = _parse_formula_md(path, prefer_ml=args.batch_ml)
    if not formulas:
        print("Error: no formulas found in file (expected markdown tables)", file=sys.stderr)
        return 1

    results = analyze(formulas, args.batch_ml)

    stem = args.output_stem or output_stem(path)
    json_p = ROOT / f"_{stem}.json"
    csv_p = ROOT / f"_{stem}.csv"

    write_json(json_p, results)
    write_csv(csv_p, results)

    if results:
        print_terminal(results, args.batch_ml)

    print(f"  JSON -> {json_p}")
    print(f"  CSV  -> {csv_p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
