"""Parse a markdown formula collection and score each build.

This is a generic parser for collection files that use the local perfume
markdown pattern:

    ## 1. FORMULA NAME
    | Layer | # | Material | Dilution | uL |

It can also apply a companion differentiation-additions markdown file with:

    ## 1. FORMULA NAME - Differentiation
    | # | Addition | Dilution | uL | Axis | Why |

Outputs are written beside the repo root as JSON and a human-readable text
report. The text report keeps the family/sub-family metadata visible so scores
can be judged inside the intended perfume category rather than as one generic
ranking.

Example:
    python scripts/score_collection_formulas.py ^
        formulas/collections/Thai_True_Mass_Market_Eighteen_2026-05-02.md ^
        --additions formulas/collections/Thai_True_Mass_Market_Eighteen_Differentiation_Additions_2026-05-02.md ^
        --label thai_true_mass_market_18
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.inventory_parser import InventoryMaterial, parse_inventory
from engine.ifra_safety import score_ifra_compliance
from engine.material_resolver import unknown_materials
from engine.optimizer.models import FormulaVector
from engine.optimizer.oav_guard import check_proportional_scaling
from engine.optimizer.scoring import FormulaScorer


MATERIAL_ALIASES = {
    "Ylang Comoros Complete": "Ylang Comoros Complete EO F3255",
    "Ylang Comoros III": "Ylang Comoros III EO F3295",
}

AXES = [
    "longevity",
    "sillage",
    "synergy",
    "luxury",
    "texture",
    "stacking_depth",
    "skin_performance",
    "hedonic",
    "perceptual_clarity",
    "photorealism",
]

REPORT_AXES = [
    "longevity",
    "sillage",
    "luxury",
    "texture",
    "stacking_depth",
    "synergy",
]

ROW_RE = re.compile(r"^\s*\|(.+)\|\s*$")
SEP_RE = re.compile(r"^\s*\|[\s:|\-]+\|\s*$")
H2_FORMULA_RE = re.compile(r"^##\s+(\d+)\.\s+(.+?)\s*$", re.MULTILINE)


@dataclass
class FormulaRecord:
    index: int
    title: str
    total_ul: float
    ingredients_ul: dict[str, float]
    dilutions: dict[str, float]
    metadata: dict[str, str]

    @property
    def n_materials(self) -> int:
        return len(self.ingredients_ul)

    def ingredients_pct(self) -> dict[str, float]:
        total = self.total_ul or sum(self.ingredients_ul.values()) or 1.0
        return {k: round(v / total * 100.0, 5) for k, v in self.ingredients_ul.items()}


def parse_dilution(value: str) -> float:
    """Convert a markdown dilution cell into an active-stock factor."""
    value = (value or "").strip().lower().replace("**", "")
    if value in ("", "-", "--", "---", "neat"):
        return 1.0
    match = re.search(r"(\d+(?:\.\d+)?)\s*%", value)
    if match:
        return float(match.group(1)) / 100.0
    return 1.0


def clean_material(name: str) -> str:
    """Strip markdown syntax while preserving useful trade-name identity."""
    name = (name or "").strip()
    name = name.replace("**", "").replace("_", "")
    name = re.sub(r"\s*\([^)]*\)\s*$", "", name)
    name = re.sub(r"^heavy\s+", "", name, flags=re.IGNORECASE)
    name = name.strip()
    return MATERIAL_ALIASES.get(name, name)


def parse_ul(value: str) -> float | None:
    value = (value or "").replace("**", "").strip()
    value = value.replace(",", "")
    match = re.search(r"-?\d+(?:\.\d+)?", value)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def parse_table_rows(text: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in text.splitlines():
        if SEP_RE.match(line):
            continue
        match = ROW_RE.match(line)
        if not match:
            continue
        rows.append([cell.strip() for cell in match.group(1).split("|")])
    return rows


def is_formula_header(cells: list[str]) -> bool:
    joined = " | ".join(cells).lower()
    return "material" in joined and ("ul" in joined or "µl" in joined)


def is_addition_header(cells: list[str]) -> bool:
    joined = " | ".join(cells).lower()
    return "addition" in joined and ("ul" in joined or "µl" in joined)


def _column(cells: list[str], predicate) -> int:
    lowered = [c.lower().replace("*", "").strip() for c in cells]
    return next((i for i, c in enumerate(lowered) if predicate(c)), -1)


def parse_formula_table(body: str) -> tuple[dict[str, float], dict[str, float], float]:
    rows = parse_table_rows(body)
    ingredients_ul: dict[str, float] = {}
    dilutions: dict[str, float] = {}
    total_ul = 0.0
    in_table = False
    material_col = -1
    dilution_col = -1
    ul_col = -1

    for cells in rows:
        if is_formula_header(cells):
            material_col = _column(cells, lambda c: "material" in c)
            dilution_col = _column(cells, lambda c: "dilution" in c)
            ul_col = _column(cells, lambda c: c == "ul" or "µl" in c)
            in_table = True
            continue

        if not in_table:
            continue
        if material_col < 0 or ul_col < 0 or len(cells) <= max(material_col, ul_col):
            in_table = False
            continue

        material_raw = cells[material_col]
        if "total" in material_raw.lower():
            in_table = False
            continue

        ul = parse_ul(cells[ul_col])
        if ul is None or ul <= 0:
            continue

        material = clean_material(material_raw)
        if not material or material in ("-", "--", "---"):
            continue

        dilution_raw = cells[dilution_col] if 0 <= dilution_col < len(cells) else "neat"
        dilution = parse_dilution(dilution_raw)
        if material in ingredients_ul:
            old_ul = ingredients_ul[material]
            new_total = old_ul + ul
            dilutions[material] = ((dilutions[material] * old_ul) + (dilution * ul)) / new_total
            ingredients_ul[material] = new_total
        else:
            ingredients_ul[material] = ul
            dilutions[material] = dilution
        total_ul += ul

    return ingredients_ul, dilutions, total_ul


def parse_collection_metadata(text: str) -> dict[int, dict[str, str]]:
    """Parse the collection's overview table if it has one."""
    metadata: dict[int, dict[str, str]] = {}
    rows = parse_table_rows(text)
    header: list[str] | None = None
    for cells in rows:
        lowered = [c.lower().replace("*", "").strip() for c in cells]
        if "#" in lowered and "name" in lowered and "family" in lowered:
            header = lowered
            continue
        if header is None:
            continue
        if len(cells) != len(header):
            if metadata:
                break
            continue
        idx_pos = header.index("#")
        idx = parse_ul(cells[idx_pos])
        if idx is None:
            continue
        row = {header[i]: cells[i].replace("**", "").strip() for i in range(len(header))}
        metadata[int(idx)] = row
    return metadata


def parse_collection(md_path: Path) -> list[FormulaRecord]:
    text = md_path.read_text(encoding="utf-8")
    metadata = parse_collection_metadata(text)
    matches = list(H2_FORMULA_RE.finditer(text))
    formulas: list[FormulaRecord] = []

    for i, match in enumerate(matches):
        idx = int(match.group(1))
        title = match.group(2).replace("**", "").strip()
        body_start = match.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[body_start:body_end]
        ingredients_ul, dilutions, total_ul = parse_formula_table(body)
        if not ingredients_ul:
            continue
        formulas.append(
            FormulaRecord(
                index=idx,
                title=title,
                total_ul=total_ul,
                ingredients_ul=ingredients_ul,
                dilutions=dilutions,
                metadata=metadata.get(idx, {}),
            )
        )
    return formulas


def parse_additions(additions_path: Path) -> dict[int, dict[str, object]]:
    text = additions_path.read_text(encoding="utf-8")
    matches = list(H2_FORMULA_RE.finditer(text))
    out: dict[int, dict[str, object]] = {}

    for i, match in enumerate(matches):
        idx = int(match.group(1))
        title = match.group(2).replace("**", "").strip()
        body_start = match.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        rows = parse_table_rows(text[body_start:body_end])
        in_table = False
        add_col = -1
        dilution_col = -1
        ul_col = -1
        axis_col = -1
        additions: list[dict[str, object]] = []

        for cells in rows:
            if is_addition_header(cells):
                add_col = _column(cells, lambda c: "addition" in c)
                dilution_col = _column(cells, lambda c: "dilution" in c)
                ul_col = _column(cells, lambda c: c == "ul" or "µl" in c)
                axis_col = _column(cells, lambda c: "axis" in c)
                in_table = True
                continue
            if not in_table:
                continue
            if add_col < 0 or ul_col < 0 or len(cells) <= max(add_col, ul_col):
                in_table = False
                continue
            material = clean_material(cells[add_col])
            ul = parse_ul(cells[ul_col])
            if not material or ul is None or ul <= 0:
                continue
            additions.append(
                {
                    "material": material,
                    "dilution": parse_dilution(cells[dilution_col]) if 0 <= dilution_col < len(cells) else 1.0,
                    "ul": ul,
                    "axis": cells[axis_col].replace("**", "").strip() if 0 <= axis_col < len(cells) else "",
                }
            )
        if additions:
            out[idx] = {"title": title, "additions": additions}

    return out


def apply_additions(formula: FormulaRecord, additions: dict[str, object]) -> FormulaRecord:
    ingredients = dict(formula.ingredients_ul)
    dilutions = dict(formula.dilutions)
    total_ul = formula.total_ul
    for item in additions.get("additions", []):  # type: ignore[union-attr]
        material = str(item["material"])  # type: ignore[index]
        ul = float(item["ul"])  # type: ignore[index]
        dilution = float(item["dilution"])  # type: ignore[index]
        if material in ingredients:
            old_ul = ingredients[material]
            new_total = old_ul + ul
            dilutions[material] = ((dilutions[material] * old_ul) + (dilution * ul)) / new_total
            ingredients[material] = new_total
        else:
            ingredients[material] = ul
            dilutions[material] = dilution
        total_ul += ul

    return FormulaRecord(
        index=formula.index,
        title=formula.title,
        total_ul=total_ul,
        ingredients_ul=ingredients,
        dilutions=dilutions,
        metadata=dict(formula.metadata),
    )


def _norm_inventory_key(name: str) -> str:
    name = name.lower()
    name = re.sub(r"#.*$", "", name)
    name = re.sub(r"\b(eo|oil|f-?tec|fleuressence|base|rectified)\b", "", name)
    name = re.sub(r"[^a-z0-9]+", " ", name)
    return " ".join(name.split())


def inventory_matches(name: str, inventory: Iterable[InventoryMaterial]) -> list[InventoryMaterial]:
    target = _norm_inventory_key(name)
    exact = []
    for record in inventory:
        if _norm_inventory_key(record.name) == target:
            exact.append(record)
    if exact:
        return exact
    fuzzy = []
    for record in inventory:
        key = _norm_inventory_key(record.name)
        if target and (target in key or key in target):
            fuzzy.append(record)
    return fuzzy


def raw_inventory_dilution(record: InventoryMaterial) -> float:
    match = re.search(r"\((\d+(?:\.\d+)?)\s*%", record.raw_name)
    if match:
        return float(match.group(1)) / 100.0
    return record.dilution


def inventory_findings(formula: FormulaRecord, inventory: list[InventoryMaterial]) -> dict[str, object]:
    not_found: list[str] = []
    dilution_mismatches: list[str] = []
    prepared_dilutions: list[str] = []
    unavailable: list[str] = []
    for material, dilution in formula.dilutions.items():
        matches = inventory_matches(material, inventory)
        if not matches:
            not_found.append(material)
            continue
        if all(record.status != "owned" for record in matches):
            unavailable.append(f"{material} ({matches[0].status})")

        inventory_dilutions = sorted({raw_inventory_dilution(record) for record in matches})
        if any(abs(candidate - dilution) <= 0.001 for candidate in inventory_dilutions):
            continue
        if dilution < 1.0 and any(abs(candidate - 1.0) <= 0.001 for candidate in inventory_dilutions):
            prepared_dilutions.append(
                f"{material}: formula uses {dilution * 100:.1f}% working dilution from neat stock"
            )
            continue
        dilution_mismatches.append(
            f"{material}: formula {dilution * 100:.1f}%, inventory "
            + "/".join(f"{candidate * 100:.1f}%" for candidate in inventory_dilutions)
        )
    return {
        "not_in_inventory": sorted(not_found),
        "dilution_mismatches": sorted(dilution_mismatches),
        "prepared_dilutions": sorted(prepared_dilutions),
        "unavailable": sorted(unavailable),
    }


def score_formula(
    formula: FormulaRecord,
    scorer: FormulaScorer,
    inventory: list[InventoryMaterial],
    *,
    source_volume_ml: float,
    target_volume_ml: float,
    variant: str,
) -> dict[str, object]:
    fv = FormulaVector(
        ingredients=formula.ingredients_pct(),
        dilutions=dict(formula.dilutions),
    )
    scores = scorer.score(fv)
    public_scores = {k: v for k, v in scores.items() if not k.startswith("_")}
    checks = check_proportional_scaling(
        formula.ingredients_ul,
        formula.dilutions,
        source_volume_ml,
        target_volume_ml,
    )
    counts = Counter(c.severity for c in checks)
    guard_items = [
        {
            "material": c.material,
            "severity": c.severity,
            "message": c.message,
            "source_oav": c.source_oav,
            "target_oav": c.target_oav,
        }
        for c in checks
        if c.severity in {"error", "warn", "info"}
    ]
    ifra = score_ifra_compliance(
        formula.ingredients_ul,
        formula.dilutions,
        total_volume_ml=source_volume_ml,
    )

    return {
        "index": formula.index,
        "title": formula.title,
        "variant": variant,
        "family": formula.metadata.get("family", ""),
        "sub_family": formula.metadata.get("sub-family", ""),
        "gender": formula.metadata.get("gender", ""),
        "format_strength": formula.metadata.get("format / strength", ""),
        "reference": formula.metadata.get("reference", ""),
        "total_ul": round(formula.total_ul, 3),
        "n_materials": formula.n_materials,
        "scores": public_scores,
        "geometric_total": scores.get("geometric_total"),
        "arithmetic_total": scores.get("arithmetic_total"),
        "hard_fail_axes": scores.get("_hard_fail_axes", []),
        "unknown_materials": unknown_materials(formula.ingredients_ul.keys()),
        "inventory_findings": inventory_findings(formula, inventory),
        "oav_guard": {
            "source_volume_ml": source_volume_ml,
            "target_volume_ml": target_volume_ml,
            "errors": counts.get("error", 0),
            "warnings": counts.get("warn", 0),
            "infos": counts.get("info", 0),
            "items": guard_items,
        },
        "ifra_safety": {
            "score": ifra.score,
            "ifra_score": ifra.ifra_score,
            "allergen_score": ifra.allergen_score,
            "violations": ifra.ifra_violations,
            "warnings": ifra.ifra_warnings,
            "allergen_declarations": ifra.allergen_declarations,
            "sensitizer_flags": ifra.sensitizer_flags,
            "banned_flags": ifra.banned_flags,
            "diagnostics": ifra.diagnostics,
        },
    }


def score_collection(
    formulas: list[FormulaRecord],
    additions: dict[int, dict[str, object]] | None,
    *,
    source_volume_ml: float,
    target_volume_ml: float,
) -> list[dict[str, object]]:
    inventory = parse_inventory(unique=False, include_solvents=True, include_unavailable=True)
    scorer = FormulaScorer()
    results: list[dict[str, object]] = []

    for formula in formulas:
        base = score_formula(
            formula,
            scorer,
            inventory,
            source_volume_ml=source_volume_ml,
            target_volume_ml=target_volume_ml,
            variant="baseline",
        )
        results.append(base)
        if additions and formula.index in additions:
            augmented_formula = apply_additions(formula, additions[formula.index])
            augmented = score_formula(
                augmented_formula,
                scorer,
                inventory,
                source_volume_ml=source_volume_ml,
                target_volume_ml=target_volume_ml,
                variant="augmented",
            )
            augmented["applied_additions"] = additions[formula.index]["additions"]
            augmented["score_delta_vs_baseline"] = {
                axis: round(
                    float(augmented["scores"].get(axis, 0.0)) - float(base["scores"].get(axis, 0.0)),
                    2,
                )
                for axis in AXES + ["arithmetic_total", "geometric_total"]
                if axis in augmented["scores"] or axis in {"arithmetic_total", "geometric_total"}
            }
            augmented["score_delta_vs_baseline"]["geometric_total"] = round(
                float(augmented.get("geometric_total") or 0.0) - float(base.get("geometric_total") or 0.0),
                2,
            )
            augmented["score_delta_vs_baseline"]["arithmetic_total"] = round(
                float(augmented.get("arithmetic_total") or 0.0) - float(base.get("arithmetic_total") or 0.0),
                2,
            )
            results.append(augmented)

    return results


def axis_summary(result: dict[str, object]) -> str:
    scores = result["scores"]  # type: ignore[index]
    assert isinstance(scores, dict)
    return " ".join(f"{axis[:4]}={float(scores.get(axis, 0.0)):4.1f}" for axis in REPORT_AXES)


def lowest_axes(result: dict[str, object], n: int = 3) -> str:
    scores = result["scores"]  # type: ignore[index]
    assert isinstance(scores, dict)
    ranked = sorted(
        ((axis, float(scores.get(axis, 0.0))) for axis in AXES if axis in scores),
        key=lambda item: item[1],
    )
    return ", ".join(f"{axis} {value:.1f}" for axis, value in ranked[:n])


def _variant_pairs(results: list[dict[str, object]]) -> list[tuple[dict[str, object], dict[str, object]]]:
    by_key: dict[int, dict[str, dict[str, object]]] = {}
    for result in results:
        by_key.setdefault(int(result["index"]), {})[str(result["variant"])] = result
    pairs = []
    for idx in sorted(by_key):
        variants = by_key[idx]
        if "baseline" in variants and "augmented" in variants:
            pairs.append((variants["baseline"], variants["augmented"]))
    return pairs


def write_text_report(
    results: list[dict[str, object]],
    out_path: Path,
    *,
    input_path: Path,
    additions_path: Path | None,
) -> None:
    lines: list[str] = []
    lines.append("=" * 120)
    lines.append("COLLECTION FORMULA SCORING REPORT")
    lines.append("=" * 120)
    lines.append(f"Input: {input_path.relative_to(ROOT)}")
    if additions_path:
        lines.append(f"Additions: {additions_path.relative_to(ROOT)}")
    lines.append("")

    baselines = [r for r in results if r["variant"] == "baseline"]
    augmented = [r for r in results if r["variant"] == "augmented"]
    lines.append(f"Parsed formulas: {len(baselines)} baseline" + (f", {len(augmented)} augmented" if augmented else ""))
    lines.append("")

    if augmented:
        lines.append("AUGMENTED DELTA SUMMARY")
        lines.append("-" * 120)
        lines.append(f"{'#':>2}  {'Name':<26} {'Family':<10} {'Geo Base':>8} {'Geo Aug':>8} {'dGeo':>7} {'dLong':>7} {'dSill':>7} {'dLux':>7} {'dTex':>7} {'dDepth':>8}")
        for base, aug in _variant_pairs(results):
            delta = aug.get("score_delta_vs_baseline", {})
            assert isinstance(delta, dict)
            name = str(base["title"]).split(" - ")[0][:26]
            lines.append(
                f"{int(base['index']):>2}  {name:<26} {str(base.get('family', ''))[:10]:<10} "
                f"{float(base.get('geometric_total') or 0.0):>8.1f} "
                f"{float(aug.get('geometric_total') or 0.0):>8.1f} "
                f"{float(delta.get('geometric_total', 0.0)):>7.1f} "
                f"{float(delta.get('longevity', 0.0)):>7.1f} "
                f"{float(delta.get('sillage', 0.0)):>7.1f} "
                f"{float(delta.get('luxury', 0.0)):>7.1f} "
                f"{float(delta.get('texture', 0.0)):>7.1f} "
                f"{float(delta.get('stacking_depth', 0.0)):>8.1f}"
            )
        lines.append("")

    lines.append("BASELINE CATEGORY SCORES")
    lines.append("-" * 120)
    for result in sorted(baselines, key=lambda r: (str(r.get("family", "")), int(r["index"]))):
        inv = result["inventory_findings"]
        guard = result["oav_guard"]
        ifra = result["ifra_safety"]
        assert isinstance(inv, dict) and isinstance(guard, dict) and isinstance(ifra, dict)
        warnings = int(guard.get("warnings", 0)) + int(guard.get("errors", 0))
        title = str(result["title"])
        lines.append(
            f"#{int(result['index']):02d} {title} | {result.get('family', '')} / {result.get('sub_family', '')} | "
            f"Geo {float(result.get('geometric_total') or 0.0):.1f}; {axis_summary(result)}"
        )
        lines.append(f"    Weak axes: {lowest_axes(result)}")
        if result.get("hard_fail_axes"):
            lines.append(f"    Hard fail axes: {result['hard_fail_axes']}")
        if result.get("unknown_materials"):
            lines.append(f"    Scorer unknown materials: {', '.join(result['unknown_materials'])}")
        if inv.get("not_in_inventory"):
            lines.append(f"    Inventory not found: {', '.join(inv['not_in_inventory'])}")
        if inv.get("dilution_mismatches"):
            lines.append(f"    Dilution mismatches: {'; '.join(inv['dilution_mismatches'])}")
        if warnings:
            lines.append(
                f"    OAV proportional-scaling guard to {guard['target_volume_ml']} mL: "
                f"{guard.get('errors', 0)} error, {guard.get('warnings', 0)} warning"
            )
        if ifra.get("violations"):
            parts = [
                f"{item['material']} {item['actual_pct']}%>{item['limit_pct']}%"
                for item in ifra["violations"]
                if isinstance(item, dict)
            ]
            lines.append(f"    IFRA Cat 4 violations: {'; '.join(parts)}")
        if ifra.get("warnings"):
            parts = [
                f"{item['material']} {item['usage_pct']}% of limit"
                for item in ifra["warnings"]
                if isinstance(item, dict)
            ]
            lines.append(f"    IFRA Cat 4 near-limit warnings: {'; '.join(parts)}")
        lines.append("")

    if augmented:
        lines.append("AUGMENTED DETAIL")
        lines.append("-" * 120)
        for result in sorted(augmented, key=lambda r: int(r["index"])):
            additions = result.get("applied_additions", [])
            assert isinstance(additions, list)
            add_text = ", ".join(
                f"{item['material']} {float(item['ul']):.0f}uL"
                for item in additions
                if isinstance(item, dict)
            )
            lines.append(
                f"#{int(result['index']):02d} {result['title']} | "
                f"Geo {float(result.get('geometric_total') or 0.0):.1f}; {axis_summary(result)}"
            )
            lines.append(f"    Added: {add_text}")
            lines.append(f"    Weak axes after additions: {lowest_axes(result)}")
            if result.get("unknown_materials"):
                lines.append(f"    Scorer unknown materials: {', '.join(result['unknown_materials'])}")
            inv = result["inventory_findings"]
            assert isinstance(inv, dict)
            if inv.get("dilution_mismatches"):
                lines.append(f"    Dilution mismatches: {'; '.join(inv['dilution_mismatches'])}")
            lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")


def output_paths(label: str) -> tuple[Path, Path]:
    return ROOT / f"_{label}_scored.json", ROOT / f"_{label}_scored.txt"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score a markdown perfume formula collection.")
    parser.add_argument("collection", type=Path, help="Markdown collection to parse.")
    parser.add_argument("--additions", type=Path, help="Optional differentiation-additions markdown.")
    parser.add_argument("--label", help="Output label. Defaults to collection stem.")
    parser.add_argument("--source-volume-ml", type=float, default=30.0)
    parser.add_argument("--target-volume-ml", type=float, default=10.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    collection = args.collection if args.collection.is_absolute() else ROOT / args.collection
    additions_path = args.additions if args.additions and args.additions.is_absolute() else (ROOT / args.additions if args.additions else None)
    label = args.label or re.sub(r"[^a-zA-Z0-9]+", "_", collection.stem).strip("_").lower()

    print(f"Reading {collection.relative_to(ROOT)}")
    formulas = parse_collection(collection)
    print(f"Parsed {len(formulas)} formulas")
    if not formulas:
        return 1

    additions = None
    if additions_path:
        print(f"Reading additions {additions_path.relative_to(ROOT)}")
        additions = parse_additions(additions_path)
        print(f"Parsed additions for {len(additions)} formulas")

    print("Scoring")
    results = score_collection(
        formulas,
        additions,
        source_volume_ml=args.source_volume_ml,
        target_volume_ml=args.target_volume_ml,
    )

    out_json, out_txt = output_paths(label)
    out_json.write_text(json.dumps(results, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    write_text_report(results, out_txt, input_path=collection, additions_path=additions_path)
    print(f"Wrote {out_json.relative_to(ROOT)}")
    print(f"Wrote {out_txt.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
