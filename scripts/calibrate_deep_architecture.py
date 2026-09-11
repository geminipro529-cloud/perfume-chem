"""Calibrate Deep Architecture family targets from the labeled reference corpus.

Corpus: ``formulas/classical_study/*.md`` (20 archetype-labelled references,
``Family archetype:`` metadata), grouped into root families via
``engine.families.registry.get_archetype(...).family``.

Method: score each reference's seven dimensions once, fit each family's target as
the per-dimension median and its range as [p10, p90], then report a
leave-one-out discrimination AUC (profiles fitted on n-1, tested on 1).

On AUC >= 0.70 it writes the fitted targets/ranges back into
``data/engine_data/deep_architecture_profiles.json``.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.families.registry import get_archetype  # noqa: E402
from engine.knowledge.deep_architecture import (  # noqa: E402
    DIMENSIONS,
    PROFILES_PATH,
    DeepArchitectureConfig,
)
from engine.optimizer.models import FormulaVector  # noqa: E402
from engine.optimizer.scoring import FormulaScorer  # noqa: E402
from scripts.verify_formula_workflow import parse_formula_markdown  # noqa: E402

STUDY_DIR = ROOT / "formulas" / "classical_study"
MIN_AUC = 0.70

_ROOT_SPECIALS = {
    "aromatic_fougere": "fougere",
    "marine": "marine_aquatic",
    "floral_bouquet": "floral",
    "iris_amber_woody": "woody",
    "iris_coumarin_amber": "woody",
    "iris_sandalwood": "woody",
    "leather_iris_amber": "leather",
    "prada_clean_iris": "woody",
    "clean_iris": "woody",
    "clean": "woody",
    "layton_dna": "oriental",
    "dior_homme_cologne": "citrus",
    "ysl_la_nuit": "oriental",
    "ysl_lhomme": "woody",
}


def root_family(family: str) -> str:
    text = str(family or "").strip().lower()
    if text in _ROOT_SPECIALS:
        return _ROOT_SPECIALS[text]
    return text.split("_")[0] or text


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 50.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    pos = (len(ordered) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    if lo == hi:
        return ordered[lo]
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo)


def load_corpus() -> list[dict]:
    rows: list[dict] = []
    for path in sorted((ROOT / "formulas").rglob("*.md")):
        if path.name.startswith("Classical_Perfume_Families_Curriculum"):
            continue
        try:
            formulas = parse_formula_markdown(path)
        except Exception:
            continue
        if not formulas:
            continue
        formula = formulas[0]
        archetype = str(formula.get("family_archetype") or "").strip()
        spec = get_archetype(archetype) if archetype else None
        if spec is None:
            continue
        rows.append({
            "file": path.name,
            "archetype": archetype,
            "family": root_family(spec.family),
            "ingredients": dict(formula.get("ingredients_ul") or {}),
            "dilutions": dict(formula.get("dilutions") or {}),
        })
    return rows


def score_rows(rows: list[dict]) -> None:
    for row in rows:
        fv = FormulaVector(ingredients=dict(row["ingredients"]), dilutions=dict(row["dilutions"]))
        block = FormulaScorer().score(
            fv, deep_architecture=DeepArchitectureConfig(enabled=True, profile=row["archetype"])
        )["deep_architecture"]
        row["dims"] = {dim: float(block["dimensions"][dim]["score"]) for dim in DIMENSIONS}


def fit(rows: list[dict]) -> dict[str, dict]:
    by_family: dict[str, list[dict]] = {}
    for row in rows:
        by_family.setdefault(row["family"], []).append(row)
    profiles: dict[str, dict] = {}
    for family, items in by_family.items():
        targets, ranges = {}, {}
        for dim in DIMENSIONS:
            values = [item["dims"][dim] for item in items]
            targets[dim] = round(statistics.median(values), 1)
            ranges[dim] = [round(percentile(values, 0.10), 1), round(percentile(values, 0.90), 1)]
        profiles[family] = {"targets": targets, "ranges": ranges}
    return profiles


def fit_score(dims: dict[str, float], profile: dict) -> float:
    """Range-based fit in [0,1]: 1 inside [p10-5,p90+5], decaying outside."""
    total = 0.0
    for dim in DIMENSIONS:
        lo, hi = profile["ranges"][dim]
        value = dims[dim]
        if lo <= value <= hi:
            total += 1.0
        else:
            delta = (lo - value) if value < lo else (value - hi)
            total += max(0.0, 1.0 - delta / 25.0)
    return total / len(DIMENSIONS)


def auc_loo(rows: list[dict]) -> tuple[float, int, int]:
    correct, pairs, skipped = 0.0, 0, 0
    for i, row in enumerate(rows):
        train = rows[:i] + rows[i + 1:]
        profiles = fit(train)
        if row["family"] not in profiles:
            skipped += 1  # singleton family in this fold
            continue
        own = fit_score(row["dims"], profiles[row["family"]])
        others = {r["family"] for r in train} - {row["family"]}
        for other in others:
            reference = fit_score(row["dims"], profiles[other])
            if own > reference:
                correct += 1.0
            elif own == reference:
                correct += 0.5
            pairs += 1
    return (correct / pairs if pairs else 0.0), pairs, skipped


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="write fitted profiles if AUC passes")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    rows = load_corpus()
    score_rows(rows)
    auc, pairs, skipped = auc_loo(rows)
    fitted = fit(rows)

    summary = {
        "corpus_files": len(rows),
        "families": {f: sum(1 for r in rows if r["family"] == f) for f in sorted({r["family"] for r in rows})},
        "leave_one_out_auc": round(auc, 3),
        "comparison_pairs": pairs,
        "skipped_singleton_folds": skipped,
        "pass": auc >= MIN_AUC,
    }

    if args.write and auc >= MIN_AUC:
        payload = json.loads(Path(PROFILES_PATH).read_text(encoding="utf-8"))
        for family, fitdata in fitted.items():
            payload["families"][family] = fitdata["targets"]
        payload["family_ranges"] = {f: fitdata["ranges"] for f, fitdata in fitted.items()}
        payload["calibration"] = {
            "method": "median target + padded [p10,p90] range from labeled classical_study corpus",
            "corpus_files": len(rows),
            "leave_one_out_auc": round(auc, 3),
        }
        Path(PROFILES_PATH).write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
        summary["written"] = str(PROFILES_PATH)

    if args.json:
        print(json.dumps(summary, indent=1))
    else:
        print(f"corpus files: {len(rows)}  families: {summary['families']}")
        print(f"leave-one-out AUC: {summary['leave_one_out_auc']} (pairs={pairs}, skipped={skipped})  pass={summary['pass']}")
        if summary.get("written"):
            print("wrote", summary["written"])
    return 0 if auc >= MIN_AUC else 1


if __name__ == "__main__":
    raise SystemExit(main())
