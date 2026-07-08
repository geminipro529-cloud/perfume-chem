"""Emit per-material ppm / ODT / OAV audit tables for a formula collection."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.ingredient_intelligence import get_profile
from engine.optimizer.oav_guard import _lookup_odt
from scripts.score_collection_formulas import FormulaRecord, parse_collection


@dataclass
class AuditRow:
    formula_index: int
    formula_title: str
    material: str
    dilution_pct: float
    stock_ul: float
    active_ul: float
    stock_pct_of_concentrate: float
    active_pct_finished: float
    active_ppm_finished: float
    odt_ppm: float | None
    oav: float | None
    oav_band: str


def band(oav: float | None) -> str:
    if oav is None:
        return "no_odt"
    if oav < 0.1:
        return "silent_<0.1x"
    if oav < 1.0:
        return "shadow_0.1-1x"
    if oav < 3.0:
        return "threshold_1-3x"
    if oav < 30.0:
        return "active_3-30x"
    if oav < 300.0:
        return "strong_30-300x"
    return "dominant_>300x"


def odt_ppm(material: str) -> float | None:
    odt = _lookup_odt(material)
    if odt is not None:
        return odt
    profile = get_profile(material)
    return getattr(profile, "odt_ppm", None) if profile else None


def audit_formula(formula: FormulaRecord, batch_ml: float) -> list[AuditRow]:
    rows: list[AuditRow] = []
    total_ul = formula.total_ul or sum(formula.ingredients_ul.values()) or 1.0
    finished_ul = batch_ml * 1000.0
    for material, stock_ul in formula.ingredients_ul.items():
        dilution = formula.dilutions.get(material, 1.0)
        active_ul = stock_ul * dilution
        ppm = active_ul / finished_ul * 1_000_000.0 if finished_ul else 0.0
        odt = odt_ppm(material)
        oav = ppm / odt if odt and odt > 0 else None
        rows.append(
            AuditRow(
                formula_index=formula.index,
                formula_title=formula.title,
                material=material,
                dilution_pct=round(dilution * 100.0, 4),
                stock_ul=round(stock_ul, 4),
                active_ul=round(active_ul, 4),
                stock_pct_of_concentrate=round(stock_ul / total_ul * 100.0, 4),
                active_pct_finished=round(active_ul / finished_ul * 100.0, 6),
                active_ppm_finished=round(ppm, 4),
                odt_ppm=round(odt, 6) if odt is not None else None,
                oav=round(oav, 4) if oav is not None else None,
                oav_band=band(oav),
            )
        )
    return rows


def audit_collection(path: Path, batch_ml: float) -> tuple[list[FormulaRecord], list[AuditRow]]:
    formulas = parse_collection(path)
    rows: list[AuditRow] = []
    for formula in formulas:
        rows.extend(audit_formula(formula, batch_ml))
    return formulas, rows


def write_csv(path: Path, rows: list[AuditRow]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(asdict(rows[0]).keys()) if rows else [])
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def fmt(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "-"
    return f"{value:,.{digits}f}"


def write_markdown(path: Path, source: Path, formulas: list[FormulaRecord], rows: list[AuditRow], batch_ml: float) -> None:
    by_formula: dict[int, list[AuditRow]] = {}
    for row in rows:
        by_formula.setdefault(row.formula_index, []).append(row)

    lines: list[str] = []
    lines.append("# PREMIUM MASS 4000+ THB UNIVERSAL EIGHTEEN - PPM / ODT / OAV AUDIT")
    lines.append("")
    lines.append("**Date:** 2026-05-02")
    lines.append(f"**Source:** `{source.as_posix()}`")
    lines.append(f"**Batch basis:** {batch_ml:g} mL finished product.")
    lines.append("**Math:** active uL = stock uL x dilution; active ppm finished = active uL / finished uL x 1,000,000; OAV = active ppm / ODT ppm.")
    lines.append("**ODT basis:** repo `engine.odor_thresholds.ODT_DATA` ethanol ppm, with `ingredient_intelligence` profile fallback where available.")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| # | Formula | Materials | ODT-covered | No ODT | Max OAV | Dominant >300x | Shadow <1x |")
    lines.append("|--:|---|--:|--:|--:|--:|--:|--:|")
    for formula in formulas:
        subset = by_formula.get(formula.index, [])
        covered = [row for row in subset if row.odt_ppm is not None]
        no_odt = len(subset) - len(covered)
        dominant = sum(1 for row in subset if row.oav is not None and row.oav >= 300)
        shadow = sum(1 for row in subset if row.oav is not None and row.oav < 1)
        max_oav = max((row.oav or 0.0 for row in subset), default=0.0)
        lines.append(
            f"| {formula.index} | {formula.title} | {len(subset)} | {len(covered)} | {no_odt} | "
            f"{max_oav:,.1f} | {dominant} | {shadow} |"
        )
    lines.append("")
    lines.append("## Per-Formula Detail")
    lines.append("")
    for formula in formulas:
        subset = sorted(by_formula.get(formula.index, []), key=lambda row: (row.oav is None, -(row.oav or 0.0)))
        lines.append(f"### {formula.index}. {formula.title}")
        lines.append("")
        lines.append("| Material | Dilution % | Stock uL | Active uL | Active ppm finished | Active % finished | ODT ppm | OAV | Band |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---|")
        for row in subset:
            lines.append(
                f"| {row.material} | {fmt(row.dilution_pct, 2)} | {fmt(row.stock_ul, 1)} | "
                f"{fmt(row.active_ul, 3)} | {fmt(row.active_ppm_finished, 2)} | "
                f"{fmt(row.active_pct_finished, 4)} | {fmt(row.odt_ppm, 4)} | "
                f"{fmt(row.oav, 1)} | {row.oav_band} |"
            )
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def output_stem(path: Path, label: str | None) -> str:
    if label:
        return re.sub(r"[^a-zA-Z0-9]+", "_", label).strip("_").lower()
    return re.sub(r"[^a-zA-Z0-9]+", "_", path.stem).strip("_").lower() + "_ppm_odt_audit"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit formula collection concentration, ppm, ODT, and OAV.")
    parser.add_argument("collection", type=Path)
    parser.add_argument("--batch-ml", type=float, default=30.0)
    parser.add_argument("--label")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    collection = args.collection if args.collection.is_absolute() else ROOT / args.collection
    formulas, rows = audit_collection(collection, args.batch_ml)
    if not formulas:
        print("No formulas parsed")
        return 1

    stem = output_stem(collection, args.label)
    md = ROOT / "formulas" / "collections" / f"{stem}.md"
    csv_path = ROOT / f"_{stem}.csv"
    json_path = ROOT / f"_{stem}.json"
    write_markdown(md, collection.relative_to(ROOT), formulas, rows, args.batch_ml)
    write_csv(csv_path, rows)
    json_path.write_text(json.dumps([asdict(row) for row in rows], indent=2, ensure_ascii=False), encoding="utf-8")
    print(md.relative_to(ROOT))
    print(csv_path.relative_to(ROOT))
    print(json_path.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
