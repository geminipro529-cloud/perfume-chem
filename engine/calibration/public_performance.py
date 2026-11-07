"""Check the gate's clock and performance read-outs against public labels.

Library module only (no CLI; AGENTS.md RULE 2). Deterministic and read-only.

Two checks, both on ``data/benchmarks/public_performance_v1.json``:

1. Strip clock. The gate's own simulator runs each material neat on a smelling strip
   (298.15 K, no ethanol). The hour at which 95 % of its moles are gone is ranked
   against The Good Scents Company's printed substantivity ("N hour(s) at 100.00 %").
2. Perfume read-outs. Repo and project reconstructions of commercial perfumes run
   through the gate's state builder and simulator. Read-outs with one free parameter
   (a skin-to-nose dilution D applied to every screening OAV) are ranked against the
   originals' Parfumo community longevity and sillage votes, with D chosen on the other
   perfumes for each held-out one.
3. Round 2 (7 Nov 2026). Read-outs with no ODT and no free parameter, declared before
   computing: long-lasting uL/mL, oil left on skin at 6 h, oil leaving at 1 h. The gate's
   score contract carries oil left at 6 h (``oil_left_contract``) with its record.

RULE 1: a screening OAV is never perceived strength. D only scales the screening OAV
before a rank comparison; nothing here converts a number into an intensity claim, and a
pass would only license a rank statement on this benchmark. Labels are benchmark data,
never material records.
"""

from __future__ import annotations

import json
import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from statistics import median
from typing import Any

BENCHMARK_ID = "public_performance_v1"
BENCHMARK_PATH = Path(__file__).resolve().parents[2] / "data" / "benchmarks" / f"{BENCHMARK_ID}.json"

# Recorded verdict of the 6 Nov 2026 run (master a45d4f70 + this module). The gate's
# score contract quotes it, so a card never presents longevity or sillage as validated.
PUBLIC_BENCHMARK_STATUS = "FAILED_PUBLIC_BENCHMARK"
PUBLIC_BENCHMARK_SUMMARY: dict[str, Any] = {
    "benchmark": BENCHMARK_ID,
    "status": PUBLIC_BENCHMARK_STATUS,
    "axes": ["longevity", "sillage", "skin_performance"],
    "finding": (
        "No gate read-out ranked 19 commercial originals' Parfumo longevity or sillage at "
        "Spearman 0.6 (best 0.47, held out 0.47); the concentrate fraction alone ranked them "
        "0.77. The strip clock tracks Good Scents substantivity (Spearman 0.69, median ratio "
        "0.7), so the gate's hours are smelling-strip hours, not skin hours."
    ),
    "claim_rule": "Do not state longevity, sillage or hours-until-faint from gate numbers.",
    "round2_finding": (
        "7 Nov 2026, read-outs declared before computing, no ODT and no free parameter: oil "
        "left on skin at 6 h ranks the 19 originals' longevity 0.86 (concentrate fraction "
        "0.77) but puts Cedrat R3.2 (judged weak) above the 6 h bottle; the composer's "
        "long-lasting uL/mL ranks them 0.57; oil leaving at 1 h ranks sillage 0.23."
    ),
}

STRIP_TEMPERATURE_K = 298.15
STRIP_GONE_FRACTION = 0.05
STRIP_HOURS: tuple[float, ...] = (
    0, 0.05, 0.1, 0.25, 0.5, 0.75, 1, 1.5, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64, 96,
    128, 168, 240, 320, 400, 600, 800, 1200, 2000,
)
STRIP_CENSOR_HOURS = 4000.0
SKIN_HOURS: tuple[float, ...] = (
    0, 0.25, 0.5, 0.75, 1, 1.5, 2, 2.5, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 16, 18, 20,
    24, 30, 36, 48,
)
DILUTION_GRID: tuple[float, ...] = tuple(10.0 ** -k for k in range(7))

MIN_ROWS = 8
CONCENTRATE_RANGE = (0.05, 0.40)
MAX_NO_OAV_SHARE = 0.10


# ---------------------------------------------------------------- statistics


def average_ranks(values: Sequence[float]) -> list[float]:
    """Return 1-based ranks, ties sharing their average rank."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for k in range(i, j + 1):
            ranks[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return ranks


def _pearson(a: Sequence[float], b: Sequence[float]) -> float | None:
    n = len(a)
    if n < 3:
        return None
    ma, mb = sum(a) / n, sum(b) / n
    va = sum((x - ma) ** 2 for x in a)
    vb = sum((y - mb) ** 2 for y in b)
    if va <= 0 or vb <= 0:
        return None
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / math.sqrt(va * vb)


def spearman(a: Sequence[float], b: Sequence[float]) -> float | None:
    """Spearman rank correlation with average ranks; None when either side is constant."""
    if len(a) != len(b):
        raise ValueError("spearman needs equal-length inputs")
    return _pearson(average_ranks(a), average_ranks(b))


# ---------------------------------------------------------------- benchmark


def load_benchmark(path: Path | str | None = None) -> dict[str, Any]:
    return json.loads(Path(path or BENCHMARK_PATH).read_text(encoding="utf-8"))


def resolve_build_path(entry: str, repo_root: Path, project_root: Path | None) -> Path | None:
    """``project:<rel>`` paths point into the project folder (studio cards stay out of the repo)."""
    if entry.startswith("project:"):
        if project_root is None:
            return None
        path = project_root / entry.removeprefix("project:")
    else:
        path = repo_root / entry
    return path if path.exists() else None


# ---------------------------------------------------------------- strip clock


def strip_life_hours(material: str, *, hours: Sequence[float] = STRIP_HOURS) -> float:
    """Hours until the gate's simulator has lost 95 % of a neat strip's moles.

    Returns ``STRIP_CENSOR_HOURS`` when the strip outlives the last window.
    """
    from engine.pipeline.simulator import simulate_formula

    frames = simulate_formula(
        {material: 20.0},
        {},
        batch_volume_ml=1.0,
        temperature_K=STRIP_TEMPERATURE_K,
        default_ethanol_fill=False,
        windows=[(f"t{h:g}", float(h) * 3600.0) for h in hours],
    )
    start = sum(m.moles for m in frames[0].state.materials)
    if start <= 0:
        raise ValueError(f"{material}: no moles on the strip")
    left = [sum(m.moles for m in f.state.materials) / start for f in frames]
    return _first_crossing(list(hours), left, STRIP_GONE_FRACTION) or STRIP_CENSOR_HOURS


def _first_crossing(hours: Sequence[float], values: Sequence[float], level: float) -> float | None:
    """First hour at which ``values`` falls to ``level``, log-interpolated in time."""
    for i in range(1, len(hours)):
        if values[i] <= level:
            a, b = values[i - 1], values[i]
            h0, h1 = max(float(hours[i - 1]), 1e-3), float(hours[i])
            if a <= level:
                return h0
            w = (a - level) / (a - b) if a != b else 1.0
            return math.exp(math.log(h0) + w * (math.log(h1) - math.log(h0)))
    return None


@dataclass(frozen=True)
class StripClockResult:
    n: int
    spearman: float | None
    median_ratio_tgsc_over_model: float | None
    rows: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "n": self.n,
            "spearman": self.spearman,
            "median_ratio_tgsc_over_model": self.median_ratio_tgsc_over_model,
            "rows": self.rows,
        }


def strip_clock_check(
    records: Sequence[Mapping[str, Any]],
    *,
    life: Callable[[str], float] = strip_life_hours,
) -> StripClockResult:
    """Rank the gate's strip life against TGSC substantivity hours (400 h is TGSC's cap)."""
    rows = []
    for rec in records:
        model_h = life(str(rec["material"]))
        rows.append({"material": rec["material"], "tgsc_hours": float(rec["hours"]), "model_hours": model_h})
    rho = spearman([r["tgsc_hours"] for r in rows], [r["model_hours"] for r in rows])
    uncensored = [
        r["tgsc_hours"] / r["model_hours"]
        for r in rows
        if r["tgsc_hours"] < 400 and 0 < r["model_hours"] < STRIP_CENSOR_HOURS
    ]
    ratio = 10 ** median(math.log10(x) for x in uncensored) if uncensored else None
    return StripClockResult(len(rows), rho, ratio, rows)


# ---------------------------------------------------------------- perfume read-outs


@dataclass(frozen=True)
class BuildRun:
    """Screening OAV and active uL per row at each window of one build."""

    path: str
    hours: tuple[float, ...]
    batch_ml: float
    rows: int
    oav: tuple[dict[str, float | None], ...]
    active_ul: tuple[dict[str, float], ...]
    no_oav_rows: tuple[str, ...]

    @property
    def concentrate_fraction(self) -> float:
        return sum(self.active_ul[0].values()) / (self.batch_ml * 1000.0)

    @property
    def no_oav_share(self) -> float:
        total = sum(self.active_ul[0].values()) or 1.0
        return sum(self.active_ul[0].get(n, 0.0) for n in self.no_oav_rows) / total


def simulate_build(
    path: Path | str,
    *,
    hours: Sequence[float] = SKIN_HOURS,
    clock_factor: float = 1.0,
) -> BuildRun:
    """Run one formula file through the gate's own state builder and simulator.

    ``clock_factor`` multiplies the simulator's loss-rate scale for this run only. The
    simulator is autonomous, so the factor rescales time and leaves the order of events
    unchanged; it lets a 48 h horizon cover what a strip-speed clock spreads over weeks.
    """
    import sys

    import engine.pipeline.simulator as sim
    from engine.pipeline.gates import ReleaseGateConfig, _gate_formula_state, _resolve_gate_config

    scripts = str(Path(__file__).resolve().parents[2] / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    from verify_formula_workflow import parse_formula_markdown

    formulas = parse_formula_markdown(Path(path))
    if not formulas:
        raise ValueError(f"{path}: no formula parsed")
    formula = max(formulas, key=lambda f: len(f.get("ingredients_ul") or {}))
    config = _resolve_gate_config(formula, ReleaseGateConfig())
    state, _, _ = _gate_formula_state(formula, config)
    base_scale = sim.LOSS_RATE_SCALE
    sim.LOSS_RATE_SCALE = base_scale * float(clock_factor)
    try:
        frames = sim.simulate_formula(
            formula["ingredients_ul"],
            formula.get("dilutions", {}),
            batch_volume_ml=config.batch_volume_ml,
            temperature_K=config.temperature_K,
            initial_state=state,
            windows=[(f"t{h:g}", float(h) * 3600.0) for h in hours],
        )
    finally:
        sim.LOSS_RATE_SCALE = base_scale
    first = frames[0].state.materials
    return BuildRun(
        path=str(path),
        hours=tuple(float(h) for h in hours),
        batch_ml=float(config.batch_volume_ml),
        rows=len(first),
        oav=tuple(
            {m.name: (float(m.screening_oav) if m.screening_oav is not None else None) for m in f.state.materials}
            for f in frames
        ),
        active_ul=tuple({m.name: float(m.active_ul or 0.0) for m in f.state.materials} for f in frames),
        no_oav_rows=tuple(m.name for m in first if m.screening_oav is None and (m.active_ul or 0) > 0),
    )


def build_drop_reason(run: BuildRun) -> str | None:
    """Parse-validity drops declared before fitting; None keeps the build."""
    if run.rows < MIN_ROWS:
        return f"fewer than {MIN_ROWS} rows parsed"
    lo, hi = CONCENTRATE_RANGE
    if not lo <= run.concentrate_fraction <= hi:
        return f"concentrate {run.concentrate_fraction:.0%} outside {lo:.0%}-{hi:.0%}"
    if run.no_oav_share > MAX_NO_OAV_SHARE:
        return f"rows without OAV hold {run.no_oav_share:.0%} of the active uL"
    if "10mL" in Path(run.path).name:
        return "file written for 10 mL; the gate reads it as 30 mL"
    return None


def hours_until_faint(run: BuildRun, dilution: float) -> float:
    """First hour at which every row's ``dilution * OAV`` is below 1 (censored at the last window)."""
    peak = [max([dilution * (o or 0.0) for o in frame.values()] + [0.0]) for frame in run.oav]
    for i in range(1, len(run.hours)):
        if peak[i] < 1.0:
            a, b = peak[i - 1], peak[i]
            if a < 1.0:
                return run.hours[i - 1]
            la, lb = math.log(a), math.log(max(b, 1e-12))
            return run.hours[i - 1] + la / (la - lb) * (run.hours[i] - run.hours[i - 1])
    return run.hours[-1]


def strength_at(run: BuildRun, dilution: float, hour: float, exponent: float = 0.5) -> float:
    """Sum of ``(dilution * OAV) ** exponent`` over rows above 1 at ``hour`` (a rank read-out only)."""
    frame = run.oav[run.hours.index(float(hour))]
    return sum((dilution * o) ** exponent for o in frame.values() if o and dilution * o > 1.0)


ReadOut = Callable[[BuildRun, float], float]

READ_OUTS: dict[str, tuple[ReadOut, str]] = {
    "hours_until_faint": (hours_until_faint, "longevity"),
    "strength_6h": (lambda run, d: strength_at(run, d, 6.0), "longevity"),
    "strength_1h": (lambda run, d: strength_at(run, d, 1.0), "sillage"),
}


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values)


def fit_read_out(
    labels: Sequence[float],
    values_by_dilution: Mapping[float, Sequence[float]],
) -> dict[str, Any]:
    """Best-D Spearman and the leave-one-out Spearman (D chosen without the held-out item)."""

    def rho(d: float, idx: Sequence[int]) -> float:
        r = spearman([labels[i] for i in idx], [values_by_dilution[d][i] for i in idx])
        return -2.0 if r is None else r

    every = range(len(labels))
    best = max(values_by_dilution, key=lambda d: rho(d, every))
    held_out = []
    for i in every:
        others = [j for j in every if j != i]
        d_i = max(values_by_dilution, key=lambda d: rho(d, others))
        held_out.append(values_by_dilution[d_i][i])
    full = spearman(labels, list(values_by_dilution[best]))
    return {"dilution": best, "spearman": full, "leave_one_out_spearman": spearman(labels, held_out)}


def evaluate_perfumes(
    benchmark: Mapping[str, Any],
    runs: Mapping[str, Sequence[BuildRun]],
    *,
    dilutions: Sequence[float] = DILUTION_GRID,
) -> dict[str, Any]:
    """Score every read-out on the originals that kept at least one valid build."""
    labels = benchmark["labels"]
    rule = benchmark["pass_rule"]
    keys = sorted(k for k, v in runs.items() if v and k in labels)
    out: dict[str, Any] = {"originals": len(keys), "builds": sum(len(runs[k]) for k in keys), "read_outs": {}}
    for name, (fn, label) in READ_OUTS.items():
        y = [float(labels[k][label]) for k in keys]
        table = {d: [_mean([fn(r, d) for r in runs[k]]) for k in keys] for d in dilutions}
        res = fit_read_out(y, table)
        res["label"] = label
        res["passes"] = bool(
            (res["spearman"] if res["spearman"] is not None else -1.0) >= rule["spearman_min"]
            and (res["leave_one_out_spearman"] if res["leave_one_out_spearman"] is not None else -1.0) > rule["leave_one_out_min"]
        )
        out["read_outs"][name] = res
    for label in ("longevity", "sillage"):
        out[f"concentrate_fraction_vs_{label}"] = spearman(
            [float(labels[k][label]) for k in keys],
            [_mean([r.concentrate_fraction for r in runs[k]]) for k in keys],
        )
    out["any_read_out_passes"] = any(v["passes"] for v in out["read_outs"].values())
    return out


def run_benchmark_builds(
    benchmark: Mapping[str, Any],
    repo_root: Path,
    project_root: Path | None = None,
    *,
    clock_factor: float = 1.0,
) -> tuple[dict[str, list[BuildRun]], list[dict[str, str]]]:
    """Simulate every listed build; return kept runs per original and the dropped builds."""
    kept: dict[str, list[BuildRun]] = {}
    dropped: list[dict[str, str]] = []
    for key, entries in benchmark["builds"].items():
        for entry in entries:
            path = resolve_build_path(entry, repo_root, project_root)
            if path is None:
                dropped.append({"original": key, "build": entry, "reason": "file not available"})
                continue
            run = simulate_build(path, clock_factor=clock_factor)
            reason = build_drop_reason(run)
            if reason:
                dropped.append({"original": key, "build": entry, "reason": reason})
            else:
                kept.setdefault(key, []).append(run)
    return kept, dropped


# ---------------------------------------------------------------- round 2: oil left on skin
#
# Declared 7 Nov 2026 before computing (benchmark ``declared_round2``): three read-outs with
# no ODT and no free parameter, so the leave-one-out ranking equals the full one. Round 1's
# OAV read-outs were set by the lowest-threshold workhorse in each build (RULE 1: OAV is
# never perceived strength); these read only volumes the gate's own simulator moves.

LONG_LASTING_VP_25C_PA = 0.1  # composition_planner.LONG_LASTING_VP_25C_PA (a test pins them equal)
OIL_LEFT_HOUR = 6.0
OIL_FLUX_WINDOW_H = (0.5, 1.5)
OIL_LEFT_STATUS = "RANKS_PUBLIC_LONGEVITY_FAILS_JUDGED_BOTTLES"


def _gate_vp_25c_pa(name: str) -> float | None:
    from engine.material_resolver import gate_vp_25c_pa

    value = gate_vp_25c_pa(name)
    return None if value is None else float(value)


def long_lasting_ul_per_ml(
    run: BuildRun, vp_25c_pa: Callable[[str], float | None] = _gate_vp_25c_pa
) -> float:
    """Active uL per mL of finished perfume in rows whose gate VP at 25 C is under 0.1 Pa.

    The composer's longevity-floor measure; a row with no VP counts as not long-lasting.
    """
    total = 0.0
    for name, ul in run.active_ul[0].items():
        vp = vp_25c_pa(name)
        if vp is not None and vp < LONG_LASTING_VP_25C_PA:
            total += ul
    return total / run.batch_ml


def oil_left_ul_per_ml(run: BuildRun, hour: float = OIL_LEFT_HOUR) -> float:
    """Active uL still on skin at ``hour`` on the gate clock, per mL of finished perfume."""
    return sum(run.active_ul[run.hours.index(float(hour))].values()) / run.batch_ml


def oil_flux_ul_per_ml_h(run: BuildRun, window: tuple[float, float] = OIL_FLUX_WINDOW_H) -> float:
    """Active uL that leaves between the window's two hours, per mL per hour."""
    start, end = (float(h) for h in window)
    gone = sum(run.active_ul[run.hours.index(start)].values()) - sum(
        run.active_ul[run.hours.index(end)].values()
    )
    return gone / run.batch_ml / (end - start)


PhysicsReadOut = Callable[[BuildRun], float]

PHYSICS_READ_OUTS: dict[str, tuple[PhysicsReadOut, str]] = {
    "long_lasting_ul_per_ml": (long_lasting_ul_per_ml, "longevity"),
    "oil_left_6h_ul_per_ml": (oil_left_ul_per_ml, "longevity"),
    "oil_flux_1h_ul_per_ml_h": (oil_flux_ul_per_ml_h, "sillage"),
}

# Kenny's judged bottles (bottle log, 4 Nov): never used to choose a read-out.
JUDGED_GOOD = "six_hour_bottle"
JUDGED_WEAK = ("cedrat_r32", "lhomme_luxe_edt")


def judged_bottles_pass(values: Mapping[str, float]) -> bool:
    """Both weak bottles strictly below the 6 h bottle."""
    good = values[JUDGED_GOOD]
    return all(values[name] < good for name in JUDGED_WEAK)


def evaluate_physics_read_outs(
    benchmark: Mapping[str, Any],
    runs: Mapping[str, Sequence[BuildRun]],
    bottles: Mapping[str, BuildRun] | None = None,
) -> dict[str, Any]:
    """Score the round-2 read-outs on the originals, and the longevity ones on the bottles."""
    labels = benchmark["labels"]
    rule = benchmark["pass_rule"]
    keys = sorted(k for k, v in runs.items() if v and k in labels)
    out: dict[str, Any] = {"originals": len(keys), "builds": sum(len(runs[k]) for k in keys), "read_outs": {}}
    baseline = {
        label: spearman(
            [float(labels[k][label]) for k in keys],
            [_mean([r.concentrate_fraction for r in runs[k]]) for k in keys],
        )
        for label in ("longevity", "sillage")
    }
    for name, (fn, label) in PHYSICS_READ_OUTS.items():
        rho = spearman([float(labels[k][label]) for k in keys], [_mean([fn(r) for r in runs[k]]) for k in keys])
        res: dict[str, Any] = {
            "label": label,
            "spearman": rho,
            "concentrate_fraction_spearman": baseline[label],
            "labels_pass": (rho if rho is not None else -1.0) >= rule["spearman_min"],
        }
        if label == "longevity" and bottles:
            values = {key: fn(run) for key, run in bottles.items()}
            res["judged_bottles"] = values
            res["judged_bottles_pass"] = judged_bottles_pass(values)
            res["passes"] = bool(res["labels_pass"] and res["judged_bottles_pass"])
        else:
            res["passes"] = bool(res["labels_pass"])
        out["read_outs"][name] = res
    out["any_read_out_passes"] = any(v["passes"] for v in out["read_outs"].values())
    return out


def formula_oil_left_ul_per_ml(state: Any, hour: float = OIL_LEFT_HOUR) -> float:
    """``oil_left_ul_per_ml`` for one gate formula state (the gate's own simulator and clock)."""
    from engine.pipeline.simulator import simulate_formula

    frames = simulate_formula(
        {}, {}, initial_state=state, windows=[("opening", 0.0), ("oil_left", float(hour) * 3600.0)]
    )
    left = sum(float(m.active_ul or 0.0) for m in frames[-1].state.materials)
    return left / float(state.batch_volume_ml)


# The gate's score contract carries this for every formula: the one number that ranks
# public longevity, with its record, so a card can compare it with the judged bottles.
OIL_LEFT_RECORD: dict[str, Any] = {
    "basis": (
        "active uL still on skin at 6 h on the gate clock (305 K, ethanol fill; "
        "strip-speed), per mL of finished perfume"
    ),
    "status": OIL_LEFT_STATUS,
    "public_longevity_spearman": 0.86,
    "concentrate_fraction_spearman": 0.77,
    "originals": 19,
    "judged_bottles_ul_per_ml": {"six_hour_bottle": 160.2, "cedrat_r32": 170.0, "lhomme_luxe_edt": 91.1},
    "claim_rule": (
        "Compare with the judged bottles only; never convert to hours or call it longevity. "
        "It does not separate Cedrat R3.2 (weak) from the 6 h bottle."
    ),
}


def oil_left_contract(state: Any) -> dict[str, Any]:
    """``OIL_LEFT_RECORD`` plus this formula's value (None, with the reason, if it can't run)."""
    out: dict[str, Any] = {"ul_per_ml": None, **OIL_LEFT_RECORD}
    try:
        out["ul_per_ml"] = round(formula_oil_left_ul_per_ml(state), 1)
    except Exception as exc:  # the score contract never fails on this read-out
        out["unavailable_reason"] = f"{type(exc).__name__}: {exc}"[:200]
    return out
