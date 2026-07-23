"""Parse Designer Prestige 18 markdown collection and score all 18 builds.

Reads:  formulas/collections/Designer_Prestige_Eighteen_3K_to_15K_THB_2026-05-02.md
Writes: _designer_prestige_18_scored.json (full scores)
        _designer_prestige_18_scored.txt  (human summary)

Run:    python scripts/score_designer_prestige_18.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.optimizer.models import FormulaVector
from engine.optimizer.scoring import FormulaScorer

COLLECTION_MD = ROOT / "formulas" / "collections" / "Designer_Prestige_Eighteen_3K_to_15K_THB_2026-05-02.md"
OUT_JSON = ROOT / "_designer_prestige_18_scored.json"
OUT_TXT = ROOT / "_designer_prestige_18_scored.txt"


# ── Dilution parsing ──────────────────────────────────────────────────────

def parse_dilution(s: str) -> float:
    """Convert dilution string to factor. neat→1.0, '10 %'→0.10, '—'→1.0 (FO/FTEC)."""
    s = s.strip().lower().replace("**", "")
    if s in ("neat", "", "—", "-"):
        return 1.0
    m = re.match(r"(\d+(?:\.\d+)?)\s*%", s)
    if m:
        return float(m.group(1)) / 100.0
    return 1.0


# ── Material name normalization ───────────────────────────────────────────

def clean_material(name: str) -> str:
    """Strip markdown bold, parentheticals, and trailing layer hints from material name."""
    name = name.strip()
    # Remove markdown bold/italic
    name = re.sub(r"\*\*", "", name)
    name = re.sub(r"_", "", name)
    # Remove trailing parentheticals like "(heart)", "(base)", "(top)", "(pear)"
    name = re.sub(r"\s*\([^)]*\)\s*$", "", name)
    # Strip leading layer-tier text occasionally embedded
    name = re.sub(r"^heavy\s+", "", name, flags=re.IGNORECASE)
    return name.strip()


# ── Markdown table row parsing ────────────────────────────────────────────

ROW_RE = re.compile(r"^\s*\|(.+)\|\s*$")
SEP_RE = re.compile(r"^\s*\|[\s:|\-]+\|\s*$")


def parse_table_block(text: str) -> list[list[str]]:
    """Extract all markdown table rows (split into cell lists) from a body of text."""
    rows = []
    for line in text.splitlines():
        if SEP_RE.match(line):
            continue
        m = ROW_RE.match(line)
        if not m:
            continue
        cells = [c.strip() for c in m.group(1).split("|")]
        rows.append(cells)
    return rows


def is_formula_header(cells: list[str]) -> bool:
    """Detect a formula table header by presence of 'Material' and 'µL' columns."""
    joined = " | ".join(cells).lower()
    return ("material" in joined and ("µl" in joined or "ul" in joined))


# ── Parse a single formula's table rows ───────────────────────────────────

def parse_formula_rows(rows: list[list[str]]) -> tuple[dict[str, float], dict[str, float], float]:
    """Given pre-extracted table rows, find the formula table and parse it.

    Returns (ingredients_ul, dilutions, total_ul). Materials listed twice (heart+base)
    are summed.
    """
    ingredients_ul: dict[str, float] = {}
    dilutions: dict[str, float] = {}
    total_ul = 0.0

    in_formula_table = False
    cols_material = -1
    cols_dilution = -1
    cols_ul = -1

    for cells in rows:
        # Detect formula table header
        if is_formula_header(cells):
            lc = [c.lower().replace("*", "") for c in cells]
            next((i for i, c in enumerate(lc) if c.strip() == "layer"), -1)
            cols_material = next((i for i, c in enumerate(lc) if "material" in c), -1)
            cols_dilution = next((i for i, c in enumerate(lc) if "dilution" in c), -1)
            cols_ul = next((i for i, c in enumerate(lc) if "µl" in c or c.strip() == "ul"), -1)
            in_formula_table = True
            continue

        if not in_formula_table:
            continue

        # Stop if we hit a row that's clearly a different table (different column count)
        if cols_material < 0 or cols_ul < 0:
            in_formula_table = False
            continue

        if len(cells) <= max(cols_material, cols_ul):
            in_formula_table = False
            continue

        material_raw = cells[cols_material]
        dilution_raw = cells[cols_dilution] if cols_dilution >= 0 and cols_dilution < len(cells) else "neat"
        ul_raw = cells[cols_ul]

        # Skip total / blank rows
        if not material_raw or not ul_raw:
            continue
        if "total" in material_raw.lower():
            in_formula_table = False
            continue

        # Try to parse µL — accept "200", "**200**", "0.5"
        ul_clean = re.sub(r"\*\*", "", ul_raw).strip()
        try:
            ul_f = float(ul_clean.replace(",", ""))
        except ValueError:
            continue

        material = clean_material(material_raw)
        if not material or material.lower() in ("—", "-", ""):
            continue
        # Skip rows that just say "covered below" or similar
        if "covered" in material.lower() or "via " in material.lower()[:4]:
            continue

        factor = parse_dilution(dilution_raw)

        # Sum if seen twice (heart + base layers)
        if material in ingredients_ul:
            # Weighted average of dilution factor by µL
            old_ul = ingredients_ul[material]
            old_factor = dilutions[material]
            new_total = old_ul + ul_f
            blended = (old_factor * old_ul + factor * ul_f) / new_total
            ingredients_ul[material] = new_total
            dilutions[material] = blended
        else:
            ingredients_ul[material] = ul_f
            dilutions[material] = factor

        total_ul += ul_f

    return ingredients_ul, dilutions, total_ul


# ── Main collection parser ────────────────────────────────────────────────

# Match formula H2 headers like "## 1. BELLE RÉVERIE — Lancôme La Vie est Belle direction"
H2_FORMULA_RE = re.compile(r"^##\s+(\d+)\.\s+(.+?)\s*$", re.MULTILINE)


def parse_collection(md_path: Path) -> list[dict]:
    text = md_path.read_text(encoding="utf-8")
    matches = list(H2_FORMULA_RE.finditer(text))

    formulas = []
    for i, m in enumerate(matches):
        idx = int(m.group(1))
        title = m.group(2).strip().replace("**", "")
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[body_start:body_end]

        rows = parse_table_block(body)
        ingredients_ul, dilutions, total_ul = parse_formula_rows(rows)

        if not ingredients_ul:
            print(f"  WARN: no ingredients parsed for #{idx} {title}")
            continue

        # Convert µL to percentage of concentrate (sum to 100)
        ingredients_pct = {k: round(v / total_ul * 100, 4) for k, v in ingredients_ul.items()}

        formulas.append({
            "index": idx,
            "title": title,
            "total_ul": total_ul,
            "n_materials": len(ingredients_ul),
            "ingredients_pct": ingredients_pct,
            "dilutions": dilutions,
        })

    return formulas


# ── Score all formulas ────────────────────────────────────────────────────

AXES = [
    "longevity", "sillage", "synergy", "luxury", "texture",
    "stacking_depth", "skin_performance", "hedonic",
    "perceptual_clarity", "photorealism",
]


def score_all(formulas: list[dict]) -> list[dict]:
    scorer = FormulaScorer()
    out = []
    for f in formulas:
        fv = FormulaVector(
            ingredients=dict(f["ingredients_pct"]),
            dilutions=dict(f["dilutions"]),
        )
        try:
            scores = scorer.score(fv)
        except Exception as e:
            print(f"  ERROR scoring #{f['index']} {f['title']}: {e}")
            continue

        # Strip private/non-serializable keys for clean output
        clean_scores = {k: v for k, v in scores.items() if not k.startswith("_")}
        out.append({
            **{k: f[k] for k in ("index", "title", "total_ul", "n_materials")},
            "scores": clean_scores,
            "geometric_total": scores.get("geometric_total"),
            "arithmetic_total": scores.get("arithmetic_total"),
        })
    return out


# ── Reporting ─────────────────────────────────────────────────────────────

def write_text_report(scored: list[dict], out_path: Path) -> None:
    lines = []
    lines.append("=" * 100)
    lines.append("DESIGNER PRESTIGE 18 — Multi-Axis Scoring Report")
    lines.append("=" * 100)
    lines.append("")
    lines.append(f"{'#':>3}  {'Title':<55}  {'GeoT':>6}  {'ArT':>6}  {'Long':>5}  {'Sill':>5}  {'Lux':>5}  {'Tex':>5}  {'Depth':>5}  {'Synrg':>5}")
    lines.append("-" * 130)

    sorted_scored = sorted(scored, key=lambda r: r.get("geometric_total") or 0, reverse=True)
    for r in sorted_scored:
        s = r["scores"]
        title = r["title"][:54]
        lines.append(
            f"{r['index']:>3}  {title:<55}  "
            f"{r.get('geometric_total', 0):>6.1f}  "
            f"{r.get('arithmetic_total', 0):>6.1f}  "
            f"{s.get('longevity', 0):>5.1f}  "
            f"{s.get('sillage', 0):>5.1f}  "
            f"{s.get('luxury', 0):>5.1f}  "
            f"{s.get('texture', 0):>5.1f}  "
            f"{s.get('stacking_depth', 0):>5.1f}  "
            f"{s.get('synergy', 0):>5.1f}  "
        )

    lines.append("")
    lines.append("=" * 100)
    lines.append("AXIS BREAKDOWN — sorted by GEOMETRIC TOTAL (descending)")
    lines.append("=" * 100)
    lines.append("")

    for r in sorted_scored:
        s = r["scores"]
        lines.append(f"#{r['index']} {r['title']}  ({r['n_materials']} materials, {r['total_ul']:.0f} µL concentrate)")
        for ax in AXES:
            v = s.get(ax)
            if v is not None:
                lines.append(f"   {ax:<22} {v:>5.1f}")
        lines.append(f"   {'arithmetic_total':<22} {s.get('arithmetic_total', 0):>5.1f}")
        lines.append(f"   {'geometric_total':<22} {s.get('geometric_total', 0):>5.1f}")
        if s.get("_hard_fail_axes"):
            lines.append(f"   ⚠ HARD FAIL AXES: {s['_hard_fail_axes']}")
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  -> wrote {out_path.relative_to(ROOT)}")


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    print(f"Reading {COLLECTION_MD.relative_to(ROOT)}...")
    formulas = parse_collection(COLLECTION_MD)
    print(f"  Parsed {len(formulas)} formulas.")
    for f in formulas:
        print(f"  #{f['index']:>2} {f['title'][:60]:<60} {f['n_materials']:>3} materials, {f['total_ul']:>6.0f} µL")

    if not formulas:
        print("No formulas parsed. Aborting.")
        return

    print(f"\nScoring all {len(formulas)} formulas...")
    scored = score_all(formulas)

    print("\nWriting results...")
    OUT_JSON.write_text(json.dumps(scored, indent=2, default=str), encoding="utf-8")
    print(f"  -> wrote {OUT_JSON.relative_to(ROOT)}")
    write_text_report(scored, OUT_TXT)

    print("\nDONE.")


if __name__ == "__main__":
    main()
