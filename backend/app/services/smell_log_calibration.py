"""Learning the time model's leaders from Kenny's nose, never silently.

Preregistered rule (schema ``smell-log-calibration-v1``; any change to the rule
below changes that version string):

* Data: per bottle and strip window inside the model's range, the model's full
  ranking of modelled materials by OAV share (a detection screen, not
  intensity, pleasantness or liking; AGENTS.md Rule 1) and the names Kenny
  marked leading or weak there. A name marked both ways in one bottle window
  counts as neither.
* Correction: one multiplicative factor per material. Over the bottle windows
  where the model ranked the material, ``net`` is +1 for each window where
  Kenny marked it leading while the model ranked it outside its top 3, and -1
  for each where the model had it in the top 3 but Kenny marked it weak.
  ``factor = exp(K * net / n_seen)`` with ``K = ln 2``, so it stays in
  [0.5, 2]. A material ranked in fewer than 3 distinct bottles keeps factor 1.
  The corrected ranking is share x factor, re-ranked (ties keep the model's
  order). The factor adjusts a ranking only; it is not an intensity.
* Baseline: the plain model's top 3 by share.
* Score per window: Kenny-leading names in the top 3 minus Kenny-weak names in
  the top 3.
* Evaluation: leave-one-bottle-out. For each bottle, fit on the other bottles
  only and score that bottle's windows; sum over every held-out window.
* Gates: at least 10 distinct bottles with a strip entry, and the corrected
  sum strictly greater than the baseline sum. Otherwise the evidence class is
  UNKNOWN and the factors are not applied anywhere.

Pure functions only: nothing here writes back to engine data or the model.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from math import exp, log
from typing import Any

SMELL_LOG_CALIBRATION_SCHEMA = "smell-log-calibration-v1"
MIN_BOTTLES = 10
MIN_BOTTLES_PER_MATERIAL = 3
TOP_N = 3
FACTOR_K = log(2)

SMELL_LOG_CALIBRATION_RULE: dict[str, Any] = {
    "schema": SMELL_LOG_CALIBRATION_SCHEMA,
    "data": "strip windows inside the model's range; model ranking by OAV share; Kenny's leads and weak",
    "factor": "exp(k * net / n_seen) per material; net = +1 lead outside top 3, -1 weak inside top 3",
    "k": "ln 2",
    "min_bottles_per_material": MIN_BOTTLES_PER_MATERIAL,
    "top_n": TOP_N,
    "baseline": "plain model top 3 by OAV share",
    "score": "per window: Kenny-leading names in top 3 minus Kenny-weak names in top 3",
    "evaluation": "leave-one-bottle-out, summed over held-out windows",
    "gates": {"min_bottles": MIN_BOTTLES, "corrected_beats_baseline": "strictly greater"},
}
SMELL_LOG_CALIBRATION_BASIS = (
    "A ranking adjustment learned from your smell log: it reorders the model's "
    "detection-screen leaders. A factor such as ×1.4 is not how strong anything smells."
)


@dataclass(frozen=True)
class CalibrationWindow:
    """One bottle's strip window: the model's ranking and what was smelled."""

    bottle_id: str
    window: str
    ranked: tuple[tuple[str, float], ...]
    leads: frozenset[str]
    weak: frozenset[str]
    n_entries: int = 1


def calibration_window(
    bottle_id: str,
    window: str,
    ranked: Sequence[tuple[str, float]],
    leads: Iterable[str],
    weak: Iterable[str],
    n_entries: int = 1,
) -> CalibrationWindow:
    """Build a window, keyed by case-folded name; a name marked both ways counts as neither."""

    lead_keys = {name.casefold() for name in leads}
    weak_keys = {name.casefold() for name in weak}
    return CalibrationWindow(
        bottle_id=bottle_id,
        window=window,
        ranked=tuple((name, share) for name, share in ranked if share > 0),
        leads=frozenset(lead_keys - weak_keys),
        weak=frozenset(weak_keys - lead_keys),
        n_entries=n_entries,
    )


def fit_factors(windows: Sequence[CalibrationWindow]) -> dict[str, dict[str, Any]]:
    """Per material (case-folded key): factor, net, n_seen, n_bottles, status and name."""

    seen: dict[str, dict[str, Any]] = {}
    for item in windows:
        for rank, (name, _share) in enumerate(item.ranked):
            key = name.casefold()
            stats = seen.setdefault(key, {"name": name, "net": 0, "n_seen": 0, "bottles": set()})
            stats["n_seen"] += 1
            stats["bottles"].add(item.bottle_id)
            if key in item.leads and rank >= TOP_N:
                stats["net"] += 1
            elif key in item.weak and rank < TOP_N:
                stats["net"] -= 1
    factors: dict[str, dict[str, Any]] = {}
    for key, stats in seen.items():
        n_bottles = len(stats["bottles"])
        enough = n_bottles >= MIN_BOTTLES_PER_MATERIAL
        factors[key] = {
            "name": stats["name"],
            "factor": exp(FACTOR_K * stats["net"] / stats["n_seen"]) if enough else 1.0,
            "net": stats["net"],
            "n_seen": stats["n_seen"],
            "n_bottles": n_bottles,
            "status": "fitted" if enough else "too few bottles",
        }
    return factors


def corrected_ranking(
    ranked: Sequence[tuple[str, float]],
    factors: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    """Names re-ranked by share x factor; ties keep the model's order."""

    scored = [
        (share * float(factors.get(name.casefold(), {}).get("factor", 1.0)), index, name)
        for index, (name, share) in enumerate(ranked)
    ]
    return [name for _score, _index, name in sorted(scored, key=lambda item: (-item[0], item[1]))]


def window_score(top: Sequence[str], window: CalibrationWindow) -> int:
    keys = [name.casefold() for name in top[:TOP_N]]
    return sum(key in window.leads for key in keys) - sum(key in window.weak for key in keys)


def window_best(window: CalibrationWindow) -> int:
    """The best score a ranking could get here: the leads the model ranks at all, up to TOP_N."""

    ranked = {name.casefold() for name, _share in window.ranked}
    return min(TOP_N, len(window.leads & ranked))


def held_out_by_bottle(windows: Sequence[CalibrationWindow]) -> list[dict[str, Any]]:
    """Per bottle, fitted on the other bottles only: its windows, both scores and the best possible."""

    rows: list[dict[str, Any]] = []
    for bottle_id in dict.fromkeys(item.bottle_id for item in windows):
        factors = fit_factors([item for item in windows if item.bottle_id != bottle_id])
        own = [item for item in windows if item.bottle_id == bottle_id]
        rows.append(
            {
                "bottle_id": bottle_id,
                "windows": [item.window for item in own],
                "baseline_score": sum(
                    window_score([name for name, _share in item.ranked], item) for item in own
                ),
                "corrected_score": sum(
                    window_score(corrected_ranking(item.ranked, factors), item) for item in own
                ),
                "best_score": sum(window_best(item) for item in own),
            }
        )
    return rows


def held_out_scores(windows: Sequence[CalibrationWindow]) -> tuple[int, int]:
    """(baseline, corrected) summed over every window, each bottle fitted without itself."""

    rows = held_out_by_bottle(windows)
    return sum(row["baseline_score"] for row in rows), sum(row["corrected_score"] for row in rows)


def _factor_label(factor: float) -> str:
    return f"×{factor:.1f}"


def chart_correction(
    name: str,
    stats: Mapping[str, Any] | None,
    calibrated: bool,
) -> dict[str, Any]:
    """One charted name: the bottles behind its correction, and the factor only when it is used."""

    used = calibrated and stats is not None and stats["status"] == "fitted"
    factor = float(stats["factor"]) if used and stats is not None else None
    return {
        "name": name,
        "n_bottles": int(stats["n_bottles"]) if stats is not None else 0,
        "min_bottles": MIN_BOTTLES_PER_MATERIAL,
        "used": used,
        "factor": round(factor, 3) if factor is not None else None,
        "label": _factor_label(factor) if factor is not None else None,
    }


def calibrate(
    windows: Sequence[CalibrationWindow],
    *,
    n_bottles_skipped: int = 0,
) -> dict[str, Any]:
    """Run the preregistered evaluation and say plainly whether the correction is used."""

    n_bottles = len({item.bottle_id for item in windows})
    held_out = held_out_by_bottle(windows)
    baseline = sum(row["baseline_score"] for row in held_out)
    corrected = sum(row["corrected_score"] for row in held_out)
    factors = fit_factors(windows)
    if n_bottles < MIN_BOTTLES:
        reason = f"{n_bottles} of {MIN_BOTTLES} bottles logged"
    elif corrected <= baseline:
        reason = (
            f"{n_bottles} bottles logged; the correction does not beat the plain model yet, "
            "so it is not used."
        )
    else:
        reason = None
    calibrated = reason is None
    return {
        "schema": SMELL_LOG_CALIBRATION_SCHEMA,
        "rule": SMELL_LOG_CALIBRATION_RULE,
        "basis": SMELL_LOG_CALIBRATION_BASIS,
        "evidence_class": "EMPIRICALLY_CALIBRATED" if calibrated else "UNKNOWN",
        "calibrated": calibrated,
        "reason": reason,
        "min_bottles": MIN_BOTTLES,
        "n_bottles": n_bottles,
        "n_bottles_skipped": n_bottles_skipped,
        "n_entries": sum(item.n_entries for item in windows),
        "n_windows": len(windows),
        "baseline_score": baseline,
        "corrected_score": corrected,
        "best_score": sum(row["best_score"] for row in held_out),
        # Display only: each bottle scored by a correction fitted without it.
        "held_out": held_out,
        "factors": [
            {
                "name": stats["name"],
                "factor": round(stats["factor"], 3),
                "label": _factor_label(stats["factor"]),
                "n_seen": stats["n_seen"],
                "n_bottles": stats["n_bottles"],
                "status": stats["status"],
            }
            for stats in sorted(factors.values(), key=lambda s: (-abs(s["net"]), s["name"]))
        ],
    }
