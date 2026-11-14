"""Backtest the release gate's performance numbers against bottles judged on skin.

Library module only (no CLI; AGENTS.md RULE 2). Deterministic and read-only.

The question: does a gate number put the bottles a wearer judged faint below the bottles
judged long-lasting, and below most gated formulas? A number that ranks a faint bottle
above the median gated formula misses it, whatever its value means.

RULE 1: every number read here is a screening output (vapour pressure screens, headspace
vapour, legacy score axes). This module only compares their rank order with what a wearer
observed. It never converts a number into perceived strength, and its result is not a
calibration: a handful of bottles can show that a number misses, never that it works.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from statistics import median
from typing import Any

AUTHORITY = "SCREENING_BACKTEST_NOT_CALIBRATION"

FAINT = "faint"
LASTING = "lasting"
UNKNOWN = "unknown"
_LABEL_ALIASES = {
    "weak": FAINT, "faint": FAINT, "short": FAINT,
    "good": LASTING, "lasting": LASTING, "long": LASTING,
}

# Wear-check keys used by the bottle log page, in minutes after application.
CHECKPOINT_MINUTES = {"m10": 10, "h1": 60, "h4": 240, "h8": 480}
# Strength scale of the bottle log page: Gone, Faint, Soft, Clear, Strong, Loud.
STRENGTH_MAX = 5
# A 4 h skin strength of Gone/Faint reads as a faint bottle; Clear or stronger as lasting.
FAINT_AT_4H_MAX = 1
LASTING_AT_4H_MIN = 3

SATURATED_SHARE = 0.5
MISS_PERCENTILE = 50.0
FLAG_PERCENTILE = 100.0 / 3.0

Extractor = Callable[[Mapping[str, Any]], float | None]


@dataclass(frozen=True, slots=True)
class MetricSpec:
    key: str
    label: str
    source: str
    longer_is: str  # "higher" or "lower": which direction the number claims is longer-lasting
    extract: Extractor


@dataclass(frozen=True, slots=True)
class Reading:
    """One gated formula with an optional wearer verdict."""

    entry_id: str
    numbers: Mapping[str, float | None]
    label: str = UNKNOWN
    group: str = "bottle"
    bottle_id: str | None = None
    note: str = ""
    strengths: Mapping[str, float] = field(default_factory=dict)


def _num(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value)


def formula_entry(report: Mapping[str, Any]) -> Mapping[str, Any]:
    """Return the first formula entry of a gate report, or the entry itself."""
    formulas = report.get("formulas")
    if isinstance(formulas, list) and formulas and isinstance(formulas[0], Mapping):
        return formulas[0]
    return report


def _gate_data(entry: Mapping[str, Any], gate_id: str) -> Mapping[str, Any]:
    for gate in entry.get("gates") or ():
        if not isinstance(gate, Mapping):
            continue
        if (gate.get("gate") or gate.get("name")) == gate_id:
            data = gate.get("data")
            return data if isinstance(data, Mapping) else {}
    return {}


def _window(entry: Mapping[str, Any], t_seconds: float) -> Mapping[str, Any]:
    for window in entry.get("time_windows") or ():
        if isinstance(window, Mapping) and _num(window.get("t_seconds")) == t_seconds:
            return window
    return {}


def _window_value(entry: Mapping[str, Any], t_seconds: float, key: str) -> float | None:
    value = _window(entry, t_seconds).get(key)
    if isinstance(value, list | tuple | dict):
        return float(len(value))
    return _num(value)


def _state(entry: Mapping[str, Any], t_seconds: float) -> Mapping[str, Any]:
    for point in entry.get("time_series") or ():
        if isinstance(point, Mapping) and _num(point.get("t_seconds")) == t_seconds:
            state = point.get("state")
            return state if isinstance(state, Mapping) else {}
    return {}


def _oil_left(t_seconds: float) -> Extractor:
    def extract(entry: Mapping[str, Any]) -> float | None:
        start = _num(_state(entry, 0.0).get("odorant_active_ul"))
        later = _num(_state(entry, t_seconds).get("odorant_active_ul"))
        if start is None or later is None or start <= 0:
            return None
        return later / start
    return extract


def _vapour_4h_over_peak(entry: Mapping[str, Any]) -> float | None:
    late = _window_value(entry, 14400.0, "total_vapor_ppm")
    early = [_window_value(entry, t, "total_vapor_ppm") for t in (0.0, 300.0, 1800.0)]
    peak = max((v for v in early if v is not None), default=None)
    if late is None or not peak:
        return None
    return late / peak


def _path(*keys: str) -> Extractor:
    def extract(entry: Mapping[str, Any]) -> float | None:
        node: Any = entry
        for key in keys:
            if not isinstance(node, Mapping):
                return None
            node = node.get(key)
        return _num(node)
    return extract


def _gate_value(gate_id: str, key: str) -> Extractor:
    def extract(entry: Mapping[str, Any]) -> float | None:
        value = _gate_data(entry, gate_id).get(key)
        if isinstance(value, list | tuple) and value:
            value = value[0]
        return _num(value)
    return extract


def _carles_base(entry: Mapping[str, Any]) -> float | None:
    data = _gate_data(entry, "carles_pyramid")
    parts = [_num(data.get("12h_heart_base")), _num(data.get("24h+_base"))]
    if any(part is None for part in parts):
        return None
    return sum(part for part in parts if part is not None)


PERFORMANCE_METRICS: tuple[MetricSpec, ...] = (
    MetricSpec("longevity", "Longevity score", "scores.longevity", "higher",
               _path("scores", "longevity")),
    MetricSpec("sillage", "Sillage score", "scores.sillage", "higher",
               _path("scores", "sillage")),
    MetricSpec("skin_performance", "Skin performance score", "scores.skin_performance", "higher",
               _path("scores", "skin_performance")),
    MetricSpec("industry_tenacity", "Tenacity (industry 10)", "industry_10.tenacity", "higher",
               _path("industry_10", "tenacity")),
    MetricSpec("industry_diffusion", "Diffusion (industry 10)", "industry_10.diffusion", "higher",
               _path("industry_10", "diffusion")),
    MetricSpec("industry_impact", "Impact (industry 10)", "industry_10.impact", "higher",
               _path("industry_10", "impact")),
    MetricSpec("industry_bloom", "Bloom (industry 10)", "industry_10.bloom", "higher",
               _path("industry_10", "bloom")),
    MetricSpec("industry_lift", "Lift (industry 10)", "industry_10.lift", "higher",
               _path("industry_10", "lift")),
    MetricSpec("long_lasting_ul_per_ml", "Long-lasting material, uL per mL",
               "tenacity_projection.long_lasting_ul_per_ml", "higher",
               _gate_value("tenacity_projection", "long_lasting_ul_per_ml")),
    MetricSpec("long_lasting_pct", "Long-lasting share of the oil",
               "tenacity_projection.long_lasting_pct", "higher",
               _gate_value("tenacity_projection", "long_lasting_pct")),
    MetricSpec("deep_pct", "Deep (VP < 0.01 Pa) share of the oil",
               "tenacity_projection.deep_pct", "higher",
               _gate_value("tenacity_projection", "deep_pct")),
    MetricSpec("concentrate_pct", "Oil in the bottle, %", "tenacity_projection.concentrate_pct",
               "higher", _gate_value("tenacity_projection", "concentrate_pct")),
    MetricSpec("vapour_2h_ppm", "Headspace vapour at 2 h, ppm",
               "time_windows[7200].total_vapor_ppm", "higher",
               lambda e: _window_value(e, 7200.0, "total_vapor_ppm")),
    MetricSpec("vapour_4h_ppm", "Headspace vapour at 4 h, ppm",
               "time_windows[14400].total_vapor_ppm", "higher",
               lambda e: _window_value(e, 14400.0, "total_vapor_ppm")),
    MetricSpec("vapour_4h_over_peak", "Vapour at 4 h / first-30-min peak",
               "time_windows total_vapor_ppm", "higher", _vapour_4h_over_peak),
    MetricSpec("perceptible_2h", "Materials above threshold at 2 h",
               "time_windows[7200].perceptible_materials", "higher",
               lambda e: _window_value(e, 7200.0, "perceptible_materials")),
    MetricSpec("perceptible_4h", "Materials above threshold at 4 h",
               "time_windows[14400].perceptible_materials", "higher",
               lambda e: _window_value(e, 14400.0, "perceptible_materials")),
    MetricSpec("subliminal_4h", "Remaining oil below threshold at 4 h (share)",
               "time_windows[14400].subliminal_mass_ratio", "lower",
               lambda e: _window_value(e, 14400.0, "subliminal_mass_ratio")),
    MetricSpec("oil_left_2h", "Simulated oil left at 2 h (share)",
               "time_series odorant_active_ul", "higher", _oil_left(7200.0)),
    MetricSpec("oil_left_4h", "Simulated oil left at 4 h (share)",
               "time_series odorant_active_ul", "higher", _oil_left(14400.0)),
    MetricSpec("carles_6h", "Carles 6 h heart class, %", "carles_pyramid.6h_heart", "higher",
               _gate_value("carles_pyramid", "6h_heart")),
    MetricSpec("carles_base", "Carles 12 h + 24 h base classes, %", "carles_pyramid", "higher",
               _carles_base),
    MetricSpec("fixative_loading", "Fixative loading", "performance_prediction.fixative_loading",
               "higher", _gate_value("performance_prediction", "fixative_loading")),
)


def extract_performance_numbers(
    report: Mapping[str, Any], specs: Sequence[MetricSpec] = PERFORMANCE_METRICS
) -> dict[str, float | None]:
    """Read every performance number from a gate report (or one formula entry)."""
    entry = formula_entry(report)
    out: dict[str, float | None] = {}
    for spec in specs:
        try:
            out[spec.key] = spec.extract(entry)
        except (TypeError, ValueError, ZeroDivisionError):
            out[spec.key] = None
    return out


def normalise_label(label: str | None) -> str:
    return _LABEL_ALIASES.get(str(label or "").strip().lower(), UNKNOWN)


def strengths_from_wears(wears: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, float]]:
    """Median strength per checkpoint per bottle, from bottle-log wear documents."""
    collected: dict[str, dict[str, list[float]]] = {}
    for wear in wears:
        bottle_id = str(wear.get("bottle_id") or "")
        checks = wear.get("checks")
        if not bottle_id or not isinstance(checks, Mapping):
            continue
        for key in CHECKPOINT_MINUTES:
            check = checks.get(key)
            strength = _num(check.get("strength")) if isinstance(check, Mapping) else None
            if strength is not None and 0 <= strength <= STRENGTH_MAX:
                collected.setdefault(bottle_id, {}).setdefault(key, []).append(strength)
    return {
        bottle: {key: float(median(values)) for key, values in checks.items()}
        for bottle, checks in collected.items()
    }


def label_from_strengths(strengths: Mapping[str, float]) -> str:
    at_4h = strengths.get("h4")
    if at_4h is None:
        return UNKNOWN
    if at_4h <= FAINT_AT_4H_MAX:
        return FAINT
    if at_4h >= LASTING_AT_4H_MIN:
        return LASTING
    return UNKNOWN


def oriented_percentile(value: float, population: Sequence[float], longer_is: str) -> float:
    """Mid-rank percentile, oriented so 100 means the number reads as longest-lasting."""
    if not population:
        raise ValueError("empty population")
    below = sum(1 for other in population if other < value)
    ties = sum(1 for other in population if other == value)
    pct = 100.0 * (below + 0.5 * ties) / len(population)
    return pct if longer_is == "higher" else 100.0 - pct


def separation(lasting: Sequence[float], faint: Sequence[float], longer_is: str) -> float | None:
    """Share of (lasting, faint) pairs the number orders correctly; ties count half."""
    if not lasting or not faint:
        return None
    sign = 1.0 if longer_is == "higher" else -1.0
    score = 0.0
    for good in lasting:
        for weak in faint:
            diff = sign * (good - weak)
            score += 1.0 if diff > 0 else 0.5 if diff == 0 else 0.0
    return score / (len(lasting) * len(faint))


def spearman(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    if len(xs) != len(ys) or len(xs) < 4:
        return None

    def ranks(values: Sequence[float]) -> list[float]:
        order = sorted(range(len(values)), key=lambda i: values[i])
        out = [0.0] * len(values)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
                j += 1
            for k in range(i, j + 1):
                out[order[k]] = (i + j) / 2.0 + 1.0
            i = j + 1
        return out

    rx, ry = ranks(xs), ranks(ys)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry, strict=True))
    vx = sum((a - mx) ** 2 for a in rx)
    vy = sum((b - my) ** 2 for b in ry)
    if vx == 0 or vy == 0:
        return None
    return cov / (vx * vy) ** 0.5


def _population_summary(values: Sequence[float]) -> dict[str, Any]:
    top = max(values)
    at_top = sum(1 for value in values if value == top)
    return {
        "n": len(values),
        "min": min(values),
        "median": float(median(values)),
        "max": top,
        "distinct": len(set(values)),
        "share_at_max": at_top / len(values),
    }


def metric_report(
    spec: MetricSpec, readings: Sequence[Reading], population: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    values = [v for v in (_num(row.get(spec.key)) for row in population) if v is not None]
    report: dict[str, Any] = {
        "key": spec.key, "label": spec.label, "source": spec.source, "longer_is": spec.longer_is,
    }
    if not values:
        report.update(verdict="no_data", population=None, readings=[])
        return report
    pop = _population_summary(values)
    saturated = pop["share_at_max"] >= SATURATED_SHARE or (pop["n"] >= 10 and pop["distinct"] <= 2)
    rows: list[dict[str, Any]] = []
    faint: list[float] = []
    lasting: list[float] = []
    faint_pcts: list[float] = []
    lasting_pcts: list[float] = []
    for reading in readings:
        value = _num(reading.numbers.get(spec.key))
        pct = None if value is None else oriented_percentile(value, values, spec.longer_is)
        rows.append({
            "entry_id": reading.entry_id, "bottle_id": reading.bottle_id, "group": reading.group,
            "label": reading.label, "value": value, "percentile": pct,
        })
        if value is None or pct is None:
            continue
        if reading.label == FAINT:
            faint.append(value)
            faint_pcts.append(pct)
        elif reading.label == LASTING:
            lasting.append(value)
            lasting_pcts.append(pct)
    sep = separation(lasting, faint, spec.longer_is)
    rated = [
        (value, r.strengths["h4"])
        for r in readings
        if "h4" in r.strengths and (value := _num(r.numbers.get(spec.key))) is not None
    ]
    rho = spearman([v for v, _ in rated], [s for _, s in rated])
    if spec.longer_is == "lower" and rho is not None:
        rho = -rho
    if saturated:
        verdict = "saturated"
    elif not faint_pcts and not lasting_pcts:
        verdict = "no_judged_bottles"
    elif any(p >= MISS_PERCENTILE for p in faint_pcts):
        verdict = "misses_faint_bottle"
    elif sep is not None and sep < 1.0:
        verdict = "misorders_bottles"
    elif faint_pcts and all(p <= FLAG_PERCENTILE for p in faint_pcts) and (
        not lasting_pcts or all(p >= MISS_PERCENTILE for p in lasting_pcts)
    ):
        verdict = "consistent_so_far"
    else:
        verdict = "unclear"
    report.update(
        verdict=verdict,
        population=pop,
        faint_percentiles=faint_pcts,
        lasting_percentiles=lasting_pcts,
        separation=sep,
        rating_rho_4h=rho,
        rating_pairs_4h=len(rated),
        readings=rows,
    )
    return report


def dedupe_population(reports: Iterable[Mapping[str, Any]]) -> list[dict[str, float | None]]:
    """Performance numbers for each distinct formula (by formula_hash) among gate reports."""
    seen: set[str] = set()
    out: list[dict[str, float | None]] = []
    for report in reports:
        entry = formula_entry(report)
        key = str(entry.get("formula_hash") or "")
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        out.append(extract_performance_numbers(entry))
    return out


def backtest(
    readings: Sequence[Reading],
    population: Sequence[Mapping[str, Any]],
    specs: Sequence[MetricSpec] = PERFORMANCE_METRICS,
) -> dict[str, Any]:
    """Rank every performance number against the judged bottles.

    ``population`` is the numbers of many gated formulas (see ``dedupe_population``); the
    readings are scored against it. Verdicts, per number:

    - ``saturated``: half or more of the population sits at the maximum, so it cannot rank.
    - ``misses_faint_bottle``: a bottle judged faint reads at or above the population median.
    - ``misorders_bottles``: a faint bottle reads as lasting at least as long as a lasting one.
    - ``consistent_so_far``: every faint bottle sits in the bottom third and every lasting
      bottle above the median. With a few bottles this is a lead to test, not a result.
    - ``unclear`` / ``no_judged_bottles`` / ``no_data``.
    """
    metrics = [metric_report(spec, readings, population) for spec in specs]
    by_verdict: dict[str, list[str]] = {}
    for metric in metrics:
        by_verdict.setdefault(metric["verdict"], []).append(metric["key"])

    def bottles(label: str) -> int:
        # Candidate cards for one bottle (version not confirmed) count once.
        return len({r.bottle_id or r.entry_id for r in readings if r.label == label})

    return {
        "authority": AUTHORITY,
        "evidence": {
            "faint_bottles": bottles(FAINT),
            "lasting_bottles": bottles(LASTING),
            "unjudged": bottles(UNKNOWN),
            "readings": len(readings),
            "population": len(population),
        },
        "by_verdict": by_verdict,
        "metrics": metrics,
    }
