"""Gate-aware optimizer repair loop.

This module does not replace existing optimizer objectives. It wraps their raw
concentrate output, runs the reusable release gates, applies deterministic
repairs for gates that can be repaired without changing the brief, and records
blocked rerun requirements for gates that need a new optimization pass.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping, Sequence

from engine.ifra_safety import IFRA_CAT4_LIMITS
from engine.inventory_parser import parse_current_inventory
from engine.name_utils import normalize_name
from engine.pipeline.audit_log import append_event, gate_report_event
from engine.pipeline.gates import GateReport, ReleaseGateConfig, gate_formula
from engine.pipeline.interventions import build_intervention_contract
from engine.pipeline.oav_authority import OAVAuthorityRequest, analyze_oav_authority
from engine.pipeline.release_scoring import compute_unified_release_scores

RawPct = Mapping[str, float]
StockDilutions = Mapping[str, float]
RepairPool = Mapping[str, float] | Sequence[str] | None
RerunCallback = Callable[[dict[str, tuple[float | None, float | None]], tuple["GateRepairAction", ...]], RawPct]


REPAIRABLE_GATES = {
    "safety_ifra_allergen",
    "pipette_floor_neat_traces",
    "exact_subtotal",
    "robustness_perturbation",
}


@dataclass(frozen=True, slots=True)
class GateRepairAction:
    """A constraint or formula mutation caused by a failed release gate."""

    pass_index: int
    gate: str
    action: str
    status: str
    material: str | None = None
    before_ul: float | None = None
    after_ul: float | None = None
    before_pct: float | None = None
    after_pct: float | None = None
    effect: str = "SAFER"
    detail: str = ""

    def as_dict(self) -> dict:
        return {
            "pass_index": self.pass_index,
            "gate": self.gate,
            "action": self.action,
            "status": self.status,
            "material": self.material,
            "before_ul": self.before_ul,
            "after_ul": self.after_ul,
            "before_pct": self.before_pct,
            "after_pct": self.after_pct,
            "effect": self.effect,
            "detail": self.detail,
        }


@dataclass(frozen=True, slots=True)
class GateAwareOptimizationResult:
    """Final result after gate repair attempts."""

    name: str
    raw_concentrate_pct: dict[str, float]
    gate_report: GateReport
    repair_actions: tuple[GateRepairAction, ...]
    iterations: int
    interventions: dict | None = None
    audit_event_id: str | None = None

    @property
    def status(self) -> str:
        return self.gate_report.status

    @property
    def commercial_readiness(self) -> str:
        return self.gate_report.commercial_readiness

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "raw_concentrate_pct": {
                key: round(value, 6)
                for key, value in self.raw_concentrate_pct.items()
            },
            "status": self.status,
            "commercial_readiness": self.commercial_readiness,
            "iterations": self.iterations,
            "audit_event_id": self.audit_event_id,
            "interventions": dict(self.interventions or {}),
            "repair_actions": [action.as_dict() for action in self.repair_actions],
            "gate_report": self.gate_report.as_dict(),
        }


def optimize_hedonic_design(
    baseline: Mapping[str, float], *,
    evaluate: Callable[[dict[str, float], str], Mapping[str, float]],
    criteria: Sequence[str], scenarios: Sequence[str],
    transfers: Sequence[tuple[str, str]], step_sizes: Sequence[float],
    bounds: Mapping[str, tuple[float, float]],
    feasible: Callable[[dict[str, float]], bool] | None = None,
    max_rounds: int = 24, min_improvement: float = 1e-6,
) -> dict:
    """Bounded computer-only pattern search, independent of release repair.

    The evaluator supplies nonnegative, comparably scaled target *losses*:
    zero means the specified design criterion is met, not proven liking.
    Each criterion in each fixed scenario is protected against regression.
    No sensory input, release gate, or aggregate release score is consumed.
    Values retain the caller's units; transfers preserve their total. Callers
    must bind exact stock forms and enforce active/carrier constraints through
    ``feasible``. This function does not create a physical mixing authorization.
    """
    import math

    criteria, scenarios = tuple(criteria), tuple(scenarios)
    transfers, step_sizes = tuple(transfers), tuple(step_sizes)
    bounds = dict(bounds)
    current = {k: float(v) for k, v in baseline.items()}
    if (not current or not criteria or not scenarios or not step_sizes
            or len(set(criteria)) != len(criteria)
            or len(set(scenarios)) != len(scenarios)
            or type(max_rounds) is not int or max_rounds < 1
            or not math.isfinite(min_improvement)
            or min_improvement <= 0
            or any(not math.isfinite(v) or v < 0 for v in current.values())
            or sum(current.values()) <= 0
            or any(not math.isfinite(s) or s <= 0 for s in step_sizes)):
        raise ValueError("Invalid search configuration")
    if set(bounds) != set(current):
        raise ValueError("Explicit bounds required for every stock")
    for name, (low, high) in bounds.items():
        if not (math.isfinite(low) and math.isfinite(high)
                and 0 <= low <= current[name] <= high):
            raise ValueError("Baseline outside finite nonnegative bounds")
    if any(a == b or a not in current or b not in current for a, b in transfers):
        raise ValueError("Transfers must name two distinct existing stocks")
    if feasible is not None and not feasible(dict(current)):
        raise ValueError("Baseline violates composition constraints")

    cache, history = {}, []
    rounds = 0

    def assess(formula):
        key = tuple(sorted(formula.items()))
        if key not in cache:
            try:
                losses = {}
                for scenario in scenarios:
                    result = evaluate(dict(formula), scenario)
                    values = {c: float(result[c]) for c in criteria}
                    if any(not math.isfinite(v) or v < 0 for v in values.values()):
                        raise ValueError("Losses must be finite and nonnegative")
                    losses[scenario] = values
                cache[key] = (losses, None)
            except Exception as exc:
                cache[key] = (None, f"{type(exc).__name__}: {exc}")
        return cache[key]

    def total(losses):
        return sum(sum(row.values()) for row in losses.values())

    def finish(status, losses, error=None):
        return {
            "status": status, "selected": dict(current),
            "baseline": dict(baseline), "losses": losses,
            "criteria": list(criteria), "scenarios": list(scenarios),
            "bounds": bounds, "transfers": list(transfers),
            "step_sizes": list(step_sizes), "rounds": rounds,
            "evaluated_candidates": len(cache), "history": history,
            "error": error, "sensory_validated": False,
            "requires_premix_trial": False,
            "claim_scope": "COMPUTATIONAL_DESIGN_ONLY",
        }

    losses, error = assess(current)
    if losses is None:
        return finish("EVALUATION_UNAVAILABLE", losses, error)
    step_index = 0
    for rounds in range(1, max_rounds + 1):
        if total(losses) == 0:
            return finish("COMPUTATIONAL_TARGET_MET", losses)
        best, best_losses, chosen = current, losses, None
        unavailable = False
        step = step_sizes[step_index]
        for donor, receiver in transfers:
            candidate = dict(current)
            candidate[donor] -= step
            candidate[receiver] += step
            entry = {"round": rounds, "donor": donor, "receiver": receiver,
                     "amount": step, "candidate": candidate, "accepted": False}
            history.append(entry)
            if any(not bounds[k][0] <= v <= bounds[k][1] for k, v in candidate.items()):
                entry["reason"] = "stock_bounds"
                continue
            if feasible is not None and not feasible(dict(candidate)):
                entry["reason"] = "composition_constraint"
                continue
            candidate_losses, error = assess(candidate)
            entry["losses"] = candidate_losses
            if candidate_losses is None:
                entry.update(reason="evaluation_unavailable", error=error)
                unavailable = True
                continue
            if any(candidate_losses[s][c] > losses[s][c] + 1e-12
                   for s in scenarios for c in criteria):
                entry["reason"] = "criterion_regression"
            elif total(best_losses) - total(candidate_losses) >= min_improvement:
                if chosen is not None:
                    chosen["reason"] = "outperformed_in_round"
                best, best_losses, chosen = candidate, candidate_losses, entry
                entry["reason"] = "improvement"
            else:
                entry["reason"] = "no_robust_improvement"
        if chosen is not None:
            chosen["accepted"] = True
            current, losses = best, best_losses
            step_index = 0
        elif unavailable:
            return finish("EVALUATION_UNAVAILABLE", losses)
        elif step_index + 1 < len(step_sizes):
            step_index += 1
        else:
            return finish("PLATEAU", losses)
    return finish("COMPUTATIONAL_TARGET_MET" if total(losses) == 0
                  else "BUDGET_EXHAUSTED", losses)


def optimize_concurrent_hedonic_design(
    baseline: Mapping[str, float], *, evaluate: Callable,
    evaluator_version: str, criteria: Sequence[str], scenarios: Sequence[str],
    lanes: Mapping[str, Sequence[tuple[str, str]]],
    step_sizes: Sequence[float], bounds: Mapping[str, tuple[float, float]],
    feasible: Callable | None = None, max_rounds: int = 12,
    max_workers: int = 4, min_improvement: float = 1e-6,
    revisions: Sequence[tuple[str, Callable]] = (),
    admission_cases: Sequence[tuple[Mapping, str, Mapping]] = (),
) -> dict:
    """Concurrent structural search with round-boundary evaluator admission.

    Callbacks must be pure, thread-safe and bounded. Losses are explicit design
    proxies, not liking probabilities. Revisions are supplied implementations,
    never self-written code or automatically weakened thresholds. Fixed admission
    cases map criteria to acceptable loss intervals. Parent selection protects
    every criterion/scenario; independent lane winners are NEVER added together.
    """
    import math
    from concurrent.futures import Future, ThreadPoolExecutor
    from copy import deepcopy
    from threading import Lock

    criteria, scenarios = tuple(criteria), tuple(scenarios)
    lanes = {name: tuple(transfers) for name, transfers in lanes.items()}
    bounds, baseline = dict(bounds), dict(baseline)
    step_sizes, revisions = tuple(step_sizes), tuple(revisions)
    admission_cases = deepcopy(tuple(admission_cases))
    versions = [evaluator_version, *(v for v, _ in revisions)]
    if (not lanes or type(max_rounds) is not int or max_rounds < 1
            or type(max_workers) is not int or max_workers < 1
            or any(not isinstance(v, str) or not v.strip() for v in versions)
            or len(set(versions)) != len(versions)
            or (revisions and not admission_cases)):
        raise ValueError("Invalid concurrent search or evaluator admission configuration")
    for _, scenario, expected in admission_cases:
        if scenario not in scenarios or set(expected) != set(criteria):
            raise ValueError("Admission cases must cover all criteria in a declared scenario")
        for low, high in expected.values():
            if not (math.isfinite(low) and math.isfinite(high) and 0 <= low <= high):
                raise ValueError("Invalid fixed admission interval")

    def cached(callback):
        cache, lock = {}, Lock()

        def call(formula, scenario):
            key = (scenario, tuple(sorted(formula.items())))
            with lock:
                owner = key not in cache
                if owner:
                    cache[key] = Future()
                future = cache[key]
            if owner:
                try:
                    values = callback(dict(formula), scenario)
                    values = {c: float(values[c]) for c in criteria}
                    if any(not math.isfinite(v) or v < 0 for v in values.values()):
                        raise ValueError("Invalid structural loss")
                    future.set_result(values)
                except Exception as exc:
                    future.set_exception(exc)
            return dict(future.result())

        return call

    active = cached(evaluate)
    current = dict(baseline)
    history, revision_history = [], []
    shortlist = {tuple(sorted(current.items())): dict(current)}

    def assess(callback, formula):
        return {s: callback(dict(formula), s) for s in scenarios}

    def total(losses):
        return sum(v for row in losses.values() for v in row.values())

    def nonregressing(candidate, incumbent):
        return all(candidate[s][c] <= incumbent[s][c] + 1e-12
                   for s in scenarios for c in criteria)

    def admit(callback):
        try:
            for formula, scenario, expected in admission_cases:
                actual = callback(dict(formula), scenario)
                if any(not low <= actual[c] <= high for c, (low, high) in expected.items()):
                    return False, "fixed_regression_case_failed"
            return True, None
        except Exception as exc:
            return False, f"{type(exc).__name__}: {exc}"

    def lane_search(transfers):
        return optimize_hedonic_design(
            current, evaluate=active, criteria=criteria, scenarios=scenarios,
            transfers=transfers, step_sizes=step_sizes, bounds=bounds,
            feasible=feasible, max_rounds=len(step_sizes),
            min_improvement=min_improvement,
        )

    # Validate through the existing controller before starting any workers.
    initial = optimize_hedonic_design(
        current, evaluate=active, criteria=criteria, scenarios=scenarios,
        transfers=(), step_sizes=step_sizes, bounds=bounds, feasible=feasible,
        max_rounds=1, min_improvement=min_improvement,
    )
    losses = initial["losses"]
    status, error = "BUDGET_EXHAUSTED", initial["error"]
    while losses is None and revisions:
        new_version, callback = revisions[0]
        revisions = revisions[1:]
        proposed = cached(callback)
        accepted, reason = admit(proposed)
        record = {"version": new_version, "accepted": accepted,
                  "reason": reason, "rescored_candidates": 0}
        if accepted:
            try:
                replacement_losses = assess(proposed, current)
                active, evaluator_version = proposed, new_version
                losses, error = replacement_losses, None
                record["rescored_candidates"] = 1
            except Exception as exc:
                record.update(accepted=False, reason=f"rescore_failed: {exc}")
        revision_history.append(record)
    if losses is None:
        status = "EVALUATION_UNAVAILABLE"
    else:
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            for round_number in range(1, max_rounds + 1):
                before = dict(current)
                frozen_version = evaluator_version
                jobs = {name: pool.submit(lane_search, transfers)
                        for name, transfers in lanes.items()}
                revision_job = None
                if round_number <= len(revisions):
                    new_version, callback = revisions[round_number - 1]
                    proposed = cached(callback)
                    revision_job = pool.submit(admit, proposed)
                lane_results = {name: job.result() for name, job in jobs.items()}
                for result in lane_results.values():
                    candidate = result["selected"]
                    shortlist[tuple(sorted(candidate.items()))] = dict(candidate)
                if revision_job is not None:
                    accepted, reason = revision_job.result()
                    record = {"version": new_version, "accepted": accepted,
                              "reason": reason, "rescored_candidates": 0}
                    if accepted:
                        try:
                            rescored = {key: assess(proposed, f)
                                        for key, f in shortlist.items()}
                            record["rescored_candidates"] = len(rescored)
                            active, evaluator_version = proposed, new_version
                            losses = rescored[tuple(sorted(current.items()))]
                        except Exception as exc:
                            record.update(accepted=False, reason=f"rescore_failed: {exc}")
                    revision_history.append(record)
                selected_lane = None
                incumbent_losses = deepcopy(losses)
                candidates = [(name, result["selected"]) for name, result in lane_results.items()
                              if result["losses"] is not None]
                if evaluator_version != frozen_version:
                    candidates.extend(("retained_shortlist", f) for f in shortlist.values())
                for name, candidate in candidates:
                    candidate_losses = assess(active, candidate)
                    if (nonregressing(candidate_losses, incumbent_losses)
                            and total(losses) - total(candidate_losses) >= min_improvement):
                        current, losses = dict(candidate), candidate_losses
                        selected_lane = name
                history.append({"round": round_number, "search_version": frozen_version,
                                "selection_version": evaluator_version,
                                "selected_lane": selected_lane, "selected": dict(current),
                                "losses": deepcopy(losses), "lanes": lane_results})
                pending_revision = round_number < len(revisions)
                if total(losses) == 0 and not pending_revision:
                    status = "COMPUTATIONAL_TARGET_MET"
                    break
                if current == before and not pending_revision and evaluator_version == frozen_version:
                    status = ("EVALUATION_UNAVAILABLE" if any(
                        r["status"] == "EVALUATION_UNAVAILABLE" for r in lane_results.values()
                    ) else "PLATEAU")
                    break
    return {"status": status, "selected": current, "baseline": baseline,
            "losses": losses, "evaluator_version": evaluator_version,
            "history": history, "revision_history": revision_history,
            "predicted_liking": None, "sensory_validated": False,
            "requires_premix_trial": False, "error": error,
            "claim_scope": "EXPERIMENTAL_STRUCTURAL_DESIGN_ONLY"}


def optimize_evidence_portfolio(
    baseline: Mapping[str, float], *, evaluate: Callable,
    evaluator_version: str, criteria: Sequence[str], scenarios: Sequence[str],
    lanes: Mapping[str, Sequence[tuple[str, str]]],
    step_sizes: Sequence[float], bounds: Mapping[str, tuple[float, float]],
    feasible: Callable | None = None, max_rounds: int = 12,
    max_candidates: int = 512, max_workers: int = 4,
    min_improvement: float = 1e-6,
) -> dict:
    """Enumerate, retain and refine an uncertainty-aware design portfolio.

    Evaluations contain ``loss_intervals`` (all criteria, lower-is-better),
    ``sources``, ``context`` equal to the scenario, and ``basis``. Explicit
    qualitative hypotheses have null intervals and cannot select a winner.
    Intervals are caller-supplied uncertainty bounds, NOT inferred confidence
    intervals. Equal interval bounds do not establish a sensory equivalence.
    Every criterion/scenario must be robustly nonregressing for advancement.
    Non-dominated alternatives survive; traversal chooses the smallest change,
    never an undocumented sum of unlike objectives. Callbacks are pure/bounded.
    This mode deliberately enumerates even when baseline losses are all zero.
    """
    import math
    from collections import Counter
    from concurrent.futures import ThreadPoolExecutor
    from copy import deepcopy

    current = {k: float(v) for k, v in baseline.items()}
    baseline, bounds = dict(current), dict(bounds)
    criteria, scenarios = tuple(criteria), tuple(scenarios)
    steps = tuple(float(s) for s in step_sizes)
    transfers = [(lane, a, b) for lane, pairs in lanes.items() for a, b in pairs]
    if (not evaluator_version or not isinstance(evaluator_version, str)
            or not evaluator_version.strip() or not lanes or not transfers
            or type(max_candidates) is not int or max_candidates < 1
            or type(max_workers) is not int or max_workers < 1):
        raise ValueError("Invalid portfolio configuration")
    # Reuse configuration/stock validation without running the real evaluator.
    optimize_hedonic_design(
        baseline, evaluate=lambda f, s: {c: 1. for c in criteria},
        criteria=criteria, scenarios=scenarios, transfers=[(a, b) for _, a, b in transfers],
        step_sizes=steps, bounds=bounds, feasible=feasible, max_rounds=max_rounds,
        min_improvement=min_improvement,
    )
    archive, history, rejected = {}, [], Counter()
    proposal_ledger = []

    def key(formula):
        return tuple(sorted(formula.items()))

    def assess(formula):
        evaluations, error, complete = {}, None, True
        for scenario in scenarios:
            row = {}
            try:
                row = deepcopy(evaluate(dict(formula), scenario))
                sources = row.get("sources")
                if (not isinstance(sources, (list, tuple)) or not sources
                        or any(not isinstance(s, str) or not s.strip() for s in sources)
                        or row.get("context") != scenario):
                    raise ValueError("Source provenance and exact scenario context required")
                intervals = row.get("loss_intervals")
                if intervals is None:
                    if row.get("basis") != "qualitative_hypothesis":
                        raise ValueError("Missing intervals require qualitative_hypothesis basis")
                    complete = False
                else:
                    if (row.get("basis") not in ("design_proxy", "validated_prediction")
                            or set(intervals) != set(criteria)):
                        raise ValueError("All declared criteria and quantitative basis required")
                    normalized = {}
                    for c in criteria:
                        low, high = map(float, intervals[c])
                        if not (math.isfinite(low) and math.isfinite(high) and 0 <= low <= high):
                            raise ValueError("Invalid loss interval")
                        normalized[c] = [low, high]
                    row["loss_intervals"] = normalized
                evaluations[scenario] = row
            except Exception as exc:
                complete = False
                error = f"{type(exc).__name__}: {exc}"
                evaluations[scenario] = {**(row if isinstance(row, dict) else {}),
                                         "loss_intervals": None, "error": error}
        return {"formula": dict(formula), "evaluations": evaluations,
                "quantitative_complete": complete, "error": error}

    def dominates(left, right):
        if not (left["quantitative_complete"] and right["quantitative_complete"]):
            return False
        strictly_better = False
        for s in scenarios:
            for c in criteria:
                lo, hi = left["evaluations"][s]["loss_intervals"][c]
                rlo, rhi = right["evaluations"][s]["loss_intervals"][c]
                if hi > rlo:
                    return False
                strictly_better |= rlo - hi >= min_improvement
        return strictly_better

    archive[key(current)] = assess(current)
    archive[key(current)]["origin"] = {"kind": "baseline"}
    status, exhausted = "BUDGET_EXHAUSTED", False
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        for round_number in range(1, max_rounds + 1):
            pending, budget_hit = {}, False
            for lane, donor, receiver in transfers:
                for step in steps:
                    candidate = dict(current)
                    candidate[donor] -= step
                    candidate[receiver] += step
                    origin = dict(lane=lane, donor=donor, receiver=receiver,
                                  amount=step, round=round_number, parent=dict(current))
                    event = {"proposal_id": len(proposal_ledger) + 1,
                             "candidate": candidate, "origin": origin,
                             "disposition": "QUEUED", "archive_index": None}
                    proposal_ledger.append(event)
                    if any(not bounds[n][0] <= v <= bounds[n][1] for n, v in candidate.items()):
                        event["disposition"] = "STOCK_BOUNDS"
                        rejected["stock_bounds"] += 1
                        continue
                    if feasible is not None and not feasible(dict(candidate)):
                        event["disposition"] = "COMPOSITION_CONSTRAINT"
                        rejected["composition_constraint"] += 1
                        continue
                    candidate_key = key(candidate)
                    if candidate_key in archive or candidate_key in pending:
                        event["disposition"] = ("DUPLICATE_ARCHIVE" if candidate_key in archive
                                                else "DUPLICATE_PENDING")
                        continue
                    if len(archive) + len(pending) >= max_candidates:
                        event["disposition"] = "BUDGET_LIMIT"
                        budget_hit = True
                        continue
                    pending[candidate_key] = (candidate, origin)
            records = pool.map(assess, (f for f, _ in pending.values()))
            for (candidate_key, (_, origin)), record in zip(pending.items(), records):
                record["origin"] = origin
                archive[candidate_key] = record
            incumbent = archive[key(current)]
            improving = [r for r in archive.values() if dominates(r, incumbent)]
            before = dict(current)
            if improving:
                chosen = min(improving, key=lambda r: (
                    sum(abs(r["formula"][n] - current[n]) for n in current),
                    key(r["formula"])))
                current = dict(chosen["formula"])
            history.append({"round": round_number, "before": before,
                            "selected": dict(current), "advanced": current != before,
                            "new_candidates": len(pending)})
            if budget_hit:
                status = "BUDGET_EXHAUSTED"
                break
            if current == before:
                exhausted = True
                if any(not r["quantitative_complete"] for r in archive.values()):
                    status = "EVIDENCE_BOUNDARY"
                elif any(r["formula"] != current and not dominates(incumbent, r)
                         for r in archive.values()):
                    status = "UNRESOLVED_COMPARISONS"
                else:
                    status = "LOCAL_PARETO_PLATEAU"
                break
    numeric = [r for r in archive.values() if r["quantitative_complete"]]
    frontier = [r for r in numeric if not any(dominates(other, r) for other in numeric)]
    indices = {k: i for i, k in enumerate(archive)}
    for event in proposal_ledger:
        if event["disposition"] in {"QUEUED", "DUPLICATE_ARCHIVE", "DUPLICATE_PENDING"}:
            candidate_key = key(event["candidate"])
            record = archive[candidate_key]
            event["archive_index"] = indices[candidate_key]
            event["evaluation_status"] = ("EVALUATION_FAILED" if record["error"] else
                                          "QUANTITATIVE" if record["quantitative_complete"]
                                          else "EVIDENCE_INCOMPLETE")
            if event["disposition"] == "QUEUED":
                event["disposition"] = "EVALUATED"
    return {"status": status, "baseline": baseline, "selected": current,
            "archive": list(archive.values()), "frontier": frontier, "history": history,
            "proposal_ledger": proposal_ledger,
            "proposal_counts": dict(Counter(e["disposition"] for e in proposal_ledger)),
            "pending_proposals": sum(e["disposition"] == "QUEUED" for e in proposal_ledger),
            "rejected_counts": dict(rejected), "neighborhood_exhausted": exhausted,
            "evaluator_version": evaluator_version, "criteria": list(criteria),
            "scenarios": list(scenarios), "evaluated_candidates": len(archive),
            "unavailable_candidates": sum(not r["quantitative_complete"] for r in archive.values()),
            "selection_authority": "DETERMINISTIC_SEARCH_REPRESENTATIVE",
            "predicted_liking": None, "sensory_validated": False,
            "requires_premix_trial": False, "claim_scope": "COMPUTATIONAL_DESIGN_ONLY"}


def optimize_global_design(
    baseline: Mapping[str, float], *, evaluate: Callable,
    bounds: Mapping[str, tuple[float, float]], feasible: Callable | None = None,
    budget: int = 64, seed: int = 17, max_workers: int = 4,
) -> dict:
    """Bounded global proposal search and an equal-cost random comparator.

    The evaluator returns ``losses`` and a declared quantitative ``basis``.
    Ranking sums caller-scaled losses; neither normalization nor sensory
    calibration is inferred. Baseline is evaluated separately and never seeds
    candidate generation. Sorted-key bounded simplex allocation is a proposal
    distribution, not a claim of uniform sampling. Half the budget explores
    globally, then multiple best seeds undergo bounded pair-transfer refinement.
    Pure, bounded, thread-safe callbacks are required. No release gate runs.
    """
    import math
    import random
    from concurrent.futures import ThreadPoolExecutor
    from copy import deepcopy

    if (not baseline or set(baseline) != set(bounds)
            or any(not isinstance(n, str) or not n for n in baseline)
            or type(budget) is not int or budget < 1
            or type(seed) is not int or type(max_workers) is not int or max_workers < 1):
        raise ValueError("Exact stock keys and positive integer search budgets required")
    names = tuple(sorted(baseline))
    parent = {n: float(baseline[n]) for n in names}
    limits = {n: tuple(map(float, bounds[n])) for n in names}
    for n in names:
        low, high = limits[n]
        if (not all(math.isfinite(v) for v in (low, high, parent[n]))
                or not 0 <= low <= parent[n] <= high):
            raise ValueError("Baseline outside finite nonnegative stock bounds")
    total = math.fsum(parent.values())
    if not math.isfinite(total) or total <= 0:
        raise ValueError("Finite positive total required")
    if feasible is not None and not feasible(dict(parent)):
        raise ValueError("Baseline violates composition constraints")
    movable = tuple(n for n in names if limits[n][0] < limits[n][1])
    rng, control_rng = random.Random(seed), random.Random(seed ^ 0x5DEECE66D)
    attempt_limit = max(200, budget * 200)
    attempts = {"optimizer": 0, "random": 0}
    rejections = {arm: {"duplicate": 0, "infeasible": 0, "bounds": 0}
                  for arm in attempts}

    def key(formula):
        return tuple(formula[n] for n in names)

    def global_point(generator):
        order = list(movable)
        generator.shuffle(order)
        point = {n: limits[n][0] for n in names}
        remaining = total - math.fsum(point.values())
        for index, n in enumerate(order):
            capacity = limits[n][1] - limits[n][0]
            rest_capacity = math.fsum(limits[m][1] - limits[m][0]
                                      for m in order[index + 1:])
            low = max(0., remaining - rest_capacity)
            high = min(capacity, remaining)
            addition = low if low >= high else generator.uniform(low, high)
            point[n] += addition
            remaining -= addition
        # Repair floating summation residual on a movable stock only.
        residual = total - math.fsum(point.values())
        for n in reversed(order):
            if limits[n][0] <= point[n] + residual <= limits[n][1]:
                point[n] += residual
                break
        return {n: point[n] for n in names}

    def admit(point, seen, arm):
        if (any(not limits[n][0] <= point[n] <= limits[n][1] for n in names)
                or not math.isclose(math.fsum(point.values()), total,
                                    rel_tol=1e-12, abs_tol=1e-10)):
            rejections[arm]["bounds"] += 1
            return False
        if key(point) in seen:
            rejections[arm]["duplicate"] += 1
            return False
        if feasible is not None and not feasible(dict(point)):
            rejections[arm]["infeasible"] += 1
            return False
        seen.add(key(point))
        return True

    def safe_diagnostics(value):
        if isinstance(value, float) and not math.isfinite(value):
            return None
        if isinstance(value, Mapping):
            return {str(k): safe_diagnostics(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [safe_diagnostics(v) for v in value]
        return value

    def assess(proposal):
        point, source = proposal
        row, losses, score, error = {}, None, None, None
        try:
            row = deepcopy(evaluate(dict(point)))
            if (not isinstance(row, Mapping) or row.get("basis") not in {
                    "experimental_design_proxy", "measured_model_prediction"}):
                raise ValueError("Declared numerical evaluator basis required")
            raw = row.get("losses")
            if (not isinstance(raw, Mapping) or not raw
                    or any(not isinstance(n, str) or not n for n in raw)
                    or any(isinstance(v, bool) or not isinstance(v, (int, float))
                           or not math.isfinite(v) or v < 0 for v in raw.values())):
                raise ValueError("Finite nonnegative numerical component losses required")
            losses = {n: float(raw[n]) for n in sorted(raw)}
            score = math.fsum(losses.values())
            if not math.isfinite(score):
                raise ValueError("Finite aggregate loss required")
        except Exception as exc:
            losses, score, error = None, None, f"{type(exc).__name__}: {exc}"
        return {"formula": dict(point), "source": source, "losses": losses,
                "score": score, "evaluation": safe_diagnostics(row),
                "valid": error is None, "error": error}

    reference = assess((parent, "baseline"))
    expected_components = tuple(reference["losses"]) if reference["valid"] else None

    def consistent(records):
        nonlocal expected_components
        for record in records:
            if not record["valid"]:
                continue
            if expected_components is None:
                expected_components = tuple(record["losses"])
            if tuple(record["losses"]) != expected_components:
                record.update(valid=False, score=None, losses=None,
                              error="ValueError: Evaluator component schema changed")
        return records

    def ranked(records):
        return sorted((r for r in records if r["valid"]),
                      key=lambda r: (r["score"], key(r["formula"])))

    # Pre-generate the independent comparator domain before adapting any search
    # proposals. Evaluate only the matching actual count, never duplicate-fill.
    control_points, control_seen = [], set()
    while len(control_points) < budget and attempts["random"] < attempt_limit:
        attempts["random"] += 1
        point = global_point(control_rng)
        if admit(point, control_seen, "random"):
            control_points.append((point, "random"))
    target = len(control_points)
    initial_target = min(target, max(1, (budget + 1) // 2))
    archive, seen = [], set()
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        proposals = []
        while len(proposals) < initial_target and attempts["optimizer"] < attempt_limit:
            attempts["optimizer"] += 1
            point = global_point(rng)
            if admit(point, seen, "optimizer"):
                proposals.append((point, "global"))
        archive.extend(consistent(list(pool.map(assess, proposals))))
        wave = 0
        while len(archive) < target and attempts["optimizer"] < attempt_limit:
            seeds = ranked(archive)[:4]
            proposals = []
            # Fixed batch size makes adaptation independent of worker count.
            while (len(proposals) < min(8, target - len(archive))
                   and attempts["optimizer"] < attempt_limit):
                attempts["optimizer"] += 1
                source = "global"
                if seeds and len(movable) >= 2 and attempts["optimizer"] % 5:
                    point = dict(seeds[len(proposals) % len(seeds)]["formula"])
                    donor, receiver = rng.sample(movable, 2)
                    available = min(point[donor] - limits[donor][0],
                                    limits[receiver][1] - point[receiver])
                    amount = available * rng.uniform(.05, .5) / (1 + wave * .25)
                    point[donor] -= amount
                    point[receiver] += amount
                    source = "refinement"
                else:
                    point = global_point(rng)
                if admit(point, seen, "optimizer"):
                    proposals.append((point, source))
            archive.extend(consistent(list(pool.map(assess, proposals))))
            wave += 1
        control = consistent(list(pool.map(assess, control_points[:len(archive)])))
    ranking, control_ranking = ranked(archive), ranked(control)
    errors = sum(not r["valid"] for r in [reference, *archive, *control])
    complete = len(archive) == len(control) == budget and errors == 0
    best = ranking[0]["score"] if ranking else None
    control_best = control_ranking[0]["score"] if control_ranking else None
    return {
        "status": ("EVALUATION_ERROR" if errors else "FINITE_BUDGET_COMPLETE" if complete
                   else "DOMAIN_OR_ATTEMPT_LIMIT"),
        "search_complete": complete, "baseline": reference, "archive": archive,
        "ranked_candidates": ranking,
        "best_observed_candidate": deepcopy(ranking[0]) if ranking else None,
        "experimental_recommendation": deepcopy(ranking[0]) if complete and ranking else None,
        "baseline_included_in_ranking": False,
        "optimizer_minus_baseline_best": (best - reference["score"]
            if best is not None and reference["valid"] else None),
        "improves_baseline_proxy": (best < reference["score"]
            if best is not None and reference["valid"] else None),
        "comparator": {"archive": control, "ranked_candidates": control_ranking,
                       "best_score": control_best, "evaluated_candidates": len(control),
                       "seed": seed ^ 0x5DEECE66D,
                       "optimizer_minus_random_best": (best - control_best
                           if best is not None and control_best is not None else None)},
        "evaluation_counts": {"baseline": 1, "optimizer": len(archive),
                              "random": len(control), "total": 1 + len(archive) + len(control)},
        "benchmark_equal_budget": len(archive) == len(control),
        "requested_budget_per_arm": budget, "attempts": attempts,
        "attempt_limit_per_arm": attempt_limit, "rejections": rejections,
        "evaluation_error_count": errors, "seed": seed,
        "aggregation": "SUM_OF_CALLER_SCALED_LOSSES",
        "selection_authority": "EXPERIMENTAL_NUMERICAL_PROXY_RANKING",
        "global_optimum_proven": False, "sensory_validated": False,
        "release_authorized": False, "predicted_liking": None,
        "claim_scope": "FINITE_BUDGET_COMPUTATIONAL_DESIGN_ONLY",
    }


def finalize_design_portfolio(result: Mapping, *, review: Mapping) -> dict:
    """Close a reviewed bounded run, not the scientific optimization problem.

    Review dispositions are parent adjudications; the CLI binds their evidence
    bytes. This function never trains/adopts a model or converts unknowns to
    losses. Budgets, evaluator errors and unreviewed proposals stay unfinished.
    """
    from copy import deepcopy

    expected, proposals = review.get("expected_proposals"), review.get("proposals")
    allowed = {"EXCLUDED", "QUALITATIVE_ONLY", "ADMITTED_NUMERIC", "PENDING"}
    if (not isinstance(expected, list) or not expected
            or any(not isinstance(x, str) or not x.strip() for x in expected)
            or len(set(expected)) != len(expected) or not isinstance(proposals, list)):
        raise ValueError("Complete evaluator proposal inventory required")
    ids = []
    for proposal in proposals:
        if (not isinstance(proposal, dict)
                or proposal.get("disposition") not in allowed
                or not isinstance(proposal.get("reason"), str) or not proposal["reason"].strip()
                or not isinstance(proposal.get("evidence"), list) or not proposal["evidence"]
                or any(not isinstance(x, str) or not x.strip() for x in proposal["evidence"])
                or not isinstance(proposal.get("id"), str)):
            raise ValueError("Every evaluator needs a disposition, reason and evidence")
        ids.append(proposal["id"])
    if len(set(ids)) != len(ids) or set(ids) != set(expected):
        raise ValueError("Evaluator proposal review is missing, duplicated or unexpected")

    from collections import Counter

    ledger = result.get("proposal_ledger")
    ledger_complete = (
        isinstance(ledger, list) and result.get("pending_proposals") == 0
        and [e.get("proposal_id") for e in ledger] == list(range(1, len(ledger) + 1))
        and all(e.get("disposition") in {
            "EVALUATED", "STOCK_BOUNDS", "COMPOSITION_CONSTRAINT",
            "DUPLICATE_ARCHIVE", "DUPLICATE_PENDING", "BUDGET_LIMIT"
        } for e in ledger)
        and dict(Counter(e["disposition"] for e in ledger)) == result.get("proposal_counts")
    )
    archive = result["archive"]
    errors = [r for r in archive if r.get("error") or any(
        e.get("error") or e.get("missing_profiles") for e in r["evaluations"].values())]
    active = [p for p in proposals if p.get("evaluator_version") == result["evaluator_version"]]
    numeric = any(r["quantitative_complete"] for r in archive)
    required_authority = "ADMITTED_NUMERIC" if numeric else "QUALITATIVE_ONLY"
    pending = [p["id"] for p in proposals if p["disposition"] == "PENDING"]
    reviewed = not pending and any(p["disposition"] == required_authority for p in active)
    if errors or not archive:
        disposition = "EVALUATION_ERROR"
    elif not ledger_complete:
        disposition = "INCOMPLETE_SEARCH"
    elif (result["status"] == "BUDGET_EXHAUSTED" or not result["neighborhood_exhausted"]
          or any(e["disposition"] == "BUDGET_LIMIT" for e in ledger)):
        disposition = "INCOMPLETE_BUDGET"
    elif not reviewed:
        disposition = "INCOMPLETE_REVIEW"
    elif result["status"] not in {
        "EVIDENCE_BOUNDARY", "LOCAL_PARETO_PLATEAU", "UNRESOLVED_COMPARISONS"
    }:
        disposition = "EVALUATION_ERROR"
    elif result["selected"] != result["baseline"]:
        disposition = "SUPPORTED_COMPUTATIONAL_CHANGE"
    else:
        disposition = "NO_SUPPORTED_CHANGE"
    complete = disposition in {"NO_SUPPORTED_CHANGE", "SUPPORTED_COMPUTATIONAL_CHANGE"}
    return {
        "disposition": disposition, "bounded_run_complete": complete,
        "search_status": result["status"],
        "selected_formula": deepcopy(result["selected"] if complete else result["baseline"]),
        "formula_action": "PROPOSE_ONLY" if complete and result["selected"] != result["baseline"]
                          else "RETAIN_BASELINE",
        "evaluator_review": deepcopy(proposals), "pending_reviews": pending,
        "evaluation_error_count": len(errors),
        "scope": "REVIEWED_EVALUATORS_AND_VISITED_NEIGHBORHOODS_ONLY",
        "global_optimum_proven": False, "hedonic_optimization_achieved": False,
        "sensory_validated": False, "requires_premix_trial": False,
        "reopen_condition": "Changed brief, stock, candidate domain, or new applicable validated evidence",
    }


def normalize_raw_pct(raw_pct: RawPct) -> dict[str, float]:
    """Normalize positive raw concentrate percentages to exactly 100%."""
    positive = {
        str(material): max(0.0, float(value or 0.0))
        for material, value in raw_pct.items()
    }
    total = sum(positive.values())
    if total <= 0:
        return {}
    return {
        material: value * 100.0 / total
        for material, value in positive.items()
        if value > 0
    }


def _inventory_stock_dilutions(
    materials: Sequence[str],
    explicit: StockDilutions,
) -> dict[str, float]:
    """Fill optimizer stock fractions from live, identity-matched inventory."""

    resolved = {str(name): float(value) for name, value in explicit.items()}
    records = parse_current_inventory(
        unique=False,
        include_solvents=True,
        include_unavailable=False,
    )
    exact: dict[str, list] = {}
    legacy: dict[str, list] = {}
    for record in records:
        exact.setdefault(
            normalize_name(record.identity_name or record.name), []
        ).append(record)
        legacy.setdefault(normalize_name(record.name), []).append(record)
    for material in materials:
        if material in resolved:
            continue
        normalized = normalize_name(material)
        candidates = exact.get(normalized) or legacy.get(normalized) or []
        if candidates:
            resolved[material] = max(record.dilution for record in candidates)
    return resolved


def raw_pct_to_formula_record(
    name: str,
    raw_pct: RawPct,
    stock_dilutions: StockDilutions | None = None,
    *,
    concentrate_ul: float = 6000.0,
    number: int = 1,
    body: str = "",
    family_archetype: str = "",
) -> dict:
    """Build the formula mapping expected by release gates."""
    normalized = normalize_raw_pct(raw_pct)
    dilutions = dict(stock_dilutions or {})
    ingredients_ul = {
        material: pct * concentrate_ul / 100.0
        for material, pct in normalized.items()
    }
    return {
        "number": number,
        "name": name,
        "body": body or name,
        "ingredients_ul": ingredients_ul,
        "ingredients_pct": normalized,
        "dilutions": {material: float(dilutions.get(material, 1.0)) for material in normalized},
        "family_archetype": family_archetype,
    }


def max_raw_ul_for_ifra(
    limit_pct: float,
    batch_volume_ml: float,
    dilution: float,
    *,
    headroom: float = 1.0,
) -> float:
    """Return the maximum raw stock uL allowed by a finished-product IFRA limit."""
    dilution = max(float(dilution or 1.0), 1e-9)
    return (float(limit_pct) * float(headroom) / 100.0) * float(batch_volume_ml) * 1000.0 / dilution


def _raw_pct_to_ul(raw_pct: RawPct, concentrate_ul: float) -> dict[str, float]:
    return {
        material: pct * concentrate_ul / 100.0
        for material, pct in normalize_raw_pct(raw_pct).items()
    }


def _ul_to_pct(raw_ul: Mapping[str, float]) -> dict[str, float]:
    total = sum(max(0.0, float(value or 0.0)) for value in raw_ul.values())
    if total <= 0:
        return {}
    return {
        material: max(0.0, float(value or 0.0)) * 100.0 / total
        for material, value in raw_ul.items()
        if value > 0
    }


def _failed_gates(report: GateReport) -> list:
    return [gate for gate in report.gates if gate.status == "FAIL"]


def _gate(report: GateReport, name: str):
    for gate in report.gates:
        if gate.gate == name:
            return gate
    return None


def _effective_ifra_headroom(config: ReleaseGateConfig) -> float:
    if hasattr(config, "effective_ifra_headroom"):
        return config.effective_ifra_headroom()
    return float(getattr(config, "ifra_headroom", 1.0) or 1.0)


def _ifra_limit_for_material(material: str) -> float | None:
    return IFRA_CAT4_LIMITS.get(material)


def _repair_pool_weights(raw_ul: Mapping[str, float], repair_pool: RepairPool, excluded: set[str]) -> dict[str, float]:
    if isinstance(repair_pool, Mapping):
        weights = {
            str(material): max(0.0, float(weight or 0.0))
            for material, weight in repair_pool.items()
            if str(material) in raw_ul and str(material) not in excluded
        }
    elif repair_pool:
        weights = {
            str(material): 1.0
            for material in repair_pool
            if str(material) in raw_ul and str(material) not in excluded
        }
    else:
        weights = {
            material: max(0.0, amount)
            for material, amount in raw_ul.items()
            if material not in excluded and amount > 0
        }

    weights = {material: weight for material, weight in weights.items() if weight > 0}
    if weights:
        return weights

    candidates = {
        material: amount
        for material, amount in raw_ul.items()
        if material not in excluded and amount > 0
    }
    if not candidates:
        return {}
    material = max(candidates, key=candidates.get)
    return {material: 1.0}


def _redistribute_ul(
    raw_ul: dict[str, float],
    excess_ul: float,
    *,
    repair_pool: RepairPool,
    excluded: set[str],
    pass_index: int,
    gate_name: str,
) -> tuple[dict[str, float], list[GateRepairAction]]:
    if excess_ul <= 1e-9:
        return raw_ul, []

    weights = _repair_pool_weights(raw_ul, repair_pool, excluded)
    if not weights:
        return raw_ul, [
            GateRepairAction(
                pass_index=pass_index,
                gate=gate_name,
                action="redistribute_excess",
                status="BLOCKED",
                before_ul=round(excess_ul, 6),
                effect="BLOCKED",
                detail="No legal repair-pool material available for displaced volume.",
            )
        ]

    total_weight = sum(weights.values())
    actions: list[GateRepairAction] = []
    for material, weight in weights.items():
        add_ul = excess_ul * weight / total_weight
        before = raw_ul.get(material, 0.0)
        raw_ul[material] = before + add_ul
        actions.append(
            GateRepairAction(
                pass_index=pass_index,
                gate=gate_name,
                action="rebalance_displaced_volume",
                status="APPLIED",
                material=material,
                before_ul=round(before, 6),
                after_ul=round(raw_ul[material], 6),
                before_pct=round(_safe_pct(before, raw_ul), 6),
                after_pct=round(_safe_pct(raw_ul[material], raw_ul), 6),
                effect="SAFER",
                detail=f"Received {add_ul:.3f} uL displaced from a hard gate repair.",
            )
        )
    return raw_ul, actions


def _safe_pct(amount_ul: float, raw_ul: Mapping[str, float]) -> float:
    total = sum(max(0.0, float(value or 0.0)) for value in raw_ul.values()) or 1.0
    return 100.0 * float(amount_ul or 0.0) / total


def _apply_ifra_repairs(
    raw_pct: RawPct,
    report: GateReport,
    stock_dilutions: StockDilutions,
    config: ReleaseGateConfig,
    *,
    concentrate_ul: float,
    repair_pool: RepairPool,
    pass_index: int,
) -> tuple[dict[str, float], list[GateRepairAction], dict[str, tuple[float | None, float | None]]]:
    safety = _gate(report, "safety_ifra_allergen")
    violations = []
    if safety:
        violations.extend(safety.data.get("violations", []) or [])
        violations.extend(safety.data.get("headroom_violations", []) or [])
    if not violations:
        return normalize_raw_pct(raw_pct), [], {}

    raw_ul = _raw_pct_to_ul(raw_pct, concentrate_ul)
    actions: list[GateRepairAction] = []
    constraints: dict[str, tuple[float | None, float | None]] = {}
    excess_total = 0.0
    excluded = set()

    for violation in violations:
        material = str(violation.get("material", ""))
        if material not in raw_ul:
            continue
        limit_pct = float(violation.get("limit_pct"))
        dilution = float(stock_dilutions.get(material, 1.0))
        current_ul = raw_ul[material]
        max_ul = max_raw_ul_for_ifra(
            limit_pct,
            config.batch_volume_ml,
            dilution,
            headroom=_effective_ifra_headroom(config),
        )
        target_ul = max(0.0, min(current_ul, max_ul - 1e-6))
        if target_ul >= current_ul:
            continue

        before_total = sum(raw_ul.values()) or concentrate_ul
        before_pct = 100.0 * current_ul / before_total
        raw_ul[material] = target_ul
        excess_total += current_ul - target_ul
        excluded.add(material)
        constraints[material] = (None, target_ul)
        actions.append(
            GateRepairAction(
                pass_index=pass_index,
                gate="safety_ifra_allergen",
                action="cap_ifra_finished_product_limit",
                status="APPLIED",
                material=material,
                before_ul=round(current_ul, 6),
                after_ul=round(target_ul, 6),
                before_pct=round(before_pct, 6),
                after_pct=round(100.0 * target_ul / before_total, 6),
                effect="SAFER",
                detail=(
                    f"IFRA Cat4 {limit_pct:.4g}% finished-product limit with "
                    f"{_effective_ifra_headroom(config):.0%} headroom; "
                    f"max raw stock {max_ul:.3f} uL at dilution {dilution:.3g}."
                ),
            )
        )

    raw_ul, redistribution = _redistribute_ul(
        raw_ul,
        excess_total,
        repair_pool=repair_pool,
        excluded=excluded,
        pass_index=pass_index,
        gate_name="safety_ifra_allergen",
    )
    actions.extend(redistribution)
    return _ul_to_pct(raw_ul), actions, constraints


def _apply_robustness_repairs(
    raw_pct: RawPct,
    report: GateReport,
    stock_dilutions: StockDilutions,
    config: ReleaseGateConfig,
    *,
    concentrate_ul: float,
    repair_pool: RepairPool,
    pass_index: int,
) -> tuple[dict[str, float], list[GateRepairAction], dict[str, tuple[float | None, float | None]]]:
    robustness = _gate(report, "robustness_perturbation")
    issues = (robustness.data.get("issues", []) if robustness else []) or []
    safety_issues = [
        issue for issue in issues
        if issue.get("safety_failed") and issue.get("direction") == "up"
    ]
    if not safety_issues:
        return normalize_raw_pct(raw_pct), [], {}

    raw_ul = _raw_pct_to_ul(raw_pct, concentrate_ul)
    actions: list[GateRepairAction] = []
    constraints: dict[str, tuple[float | None, float | None]] = {}
    excess_total = 0.0
    excluded = set()

    for issue in safety_issues:
        material = str(issue.get("material", ""))
        if material not in raw_ul:
            continue
        current_ul = raw_ul[material]
        delta_ul = max(0.0, float(issue.get("delta_ul", 0.0) or 0.0))
        limit = _ifra_limit_for_material(material)
        dilution = float(stock_dilutions.get(material, 1.0))
        headroom_cap = current_ul
        if limit is not None:
            headroom_cap = max_raw_ul_for_ifra(
                limit,
                config.batch_volume_ml,
                dilution,
                headroom=_effective_ifra_headroom(config),
            )
        perturbation_cap = max(0.0, current_ul - delta_ul)
        target_ul = max(0.0, min(current_ul, perturbation_cap, headroom_cap - 1e-6))
        if target_ul >= current_ul:
            continue

        before_total = sum(raw_ul.values()) or concentrate_ul
        before_pct = 100.0 * current_ul / before_total
        raw_ul[material] = target_ul
        excess_total += current_ul - target_ul
        excluded.add(material)
        constraints[material] = (None, target_ul)
        actions.append(
            GateRepairAction(
                pass_index=pass_index,
                gate="robustness_perturbation",
                action="cap_robustness_safety_margin",
                status="APPLIED",
                material=material,
                before_ul=round(current_ul, 6),
                after_ul=round(target_ul, 6),
                before_pct=round(before_pct, 6),
                after_pct=round(100.0 * target_ul / before_total, 6),
                effect="SAFER",
                detail=(
                    f"Material-up perturbation of {delta_ul:.3f} uL caused safety failure; "
                    f"cap uses min(current-delta={perturbation_cap:.3f}, "
                    f"headroom-cap={headroom_cap:.3f})."
                ),
            )
        )

    raw_ul, redistribution = _redistribute_ul(
        raw_ul,
        excess_total,
        repair_pool=repair_pool,
        excluded=excluded,
        pass_index=pass_index,
        gate_name="robustness_perturbation",
    )
    actions.extend(redistribution)
    return _ul_to_pct(raw_ul), actions, constraints


def _apply_pipette_repairs(
    raw_pct: RawPct,
    stock_dilutions: StockDilutions,
    config: ReleaseGateConfig,
    *,
    concentrate_ul: float,
    pass_index: int,
) -> tuple[dict[str, float], list[GateRepairAction]]:
    raw_ul = _raw_pct_to_ul(raw_pct, concentrate_ul)
    actions: list[GateRepairAction] = []

    for material, amount_ul in list(raw_ul.items()):
        dilution = float(stock_dilutions.get(material, 1.0))
        if amount_ul <= 0 or amount_ul >= config.min_neat_trace_ul or dilution < 0.999:
            continue

        deficit = config.min_neat_trace_ul - amount_ul
        donors = {
            donor: amount
            for donor, amount in raw_ul.items()
            if donor != material and amount > config.min_neat_trace_ul + deficit
        }
        if not donors:
            actions.append(
                GateRepairAction(
                    pass_index=pass_index,
                    gate="pipette_floor_neat_traces",
                    action="raise_neat_trace_to_floor",
                    status="BLOCKED",
                    material=material,
                    before_ul=round(amount_ul, 6),
                    after_ul=round(config.min_neat_trace_ul, 6),
                    effect="BUILDABILITY",
                    detail="No donor material had enough volume to preserve subtotal.",
                )
            )
            continue

        donor = max(donors, key=donors.get)
        donor_before = raw_ul[donor]
        raw_ul[material] = config.min_neat_trace_ul
        raw_ul[donor] = donor_before - deficit
        actions.append(
            GateRepairAction(
                pass_index=pass_index,
                gate="pipette_floor_neat_traces",
                action="raise_neat_trace_to_floor",
                status="APPLIED",
                material=material,
                before_ul=round(amount_ul, 6),
                after_ul=round(config.min_neat_trace_ul, 6),
                effect="BUILDABILITY",
                detail=f"Moved {deficit:.3f} uL from {donor}.",
            )
        )

    return _ul_to_pct(raw_ul), actions


def _nonrepairable_actions(report: GateReport, pass_index: int) -> list[GateRepairAction]:
    actions: list[GateRepairAction] = []
    for gate in _failed_gates(report):
        if gate.gate in REPAIRABLE_GATES:
            continue
        action = "block_unknown_or_forbidden_material"
        effect = "BLOCKED"
        if gate.gate in {"perfumer_logic", "fougere_skeleton", "chypre_skeleton"}:
            action = "rerun_with_tighter_brief_grammar"
            effect = "BRIEF_FIT"
        elif gate.gate in {"material_spine_coverage", "physics_data_coverage", "odt_coverage"}:
            action = "block_missing_material_data"
        elif gate.gate == "chemistry_stability":
            action = "rerun_with_stability_constraints"
            effect = "CHEMISTRY"
        elif gate.gate == "phase_compatibility":
            action = "rerun_with_phase_compatibility_constraints"
            effect = "CHEMISTRY"
        elif gate.gate == "opaque_preblends":
            action = "block_opaque_preblend"
        actions.append(
            GateRepairAction(
                pass_index=pass_index,
                gate=gate.gate,
                action=action,
                status="BLOCKED",
                effect=effect,
                detail=gate.detail,
            )
        )
    return actions


def optimize_until_release_ready(
    name: str,
    raw_concentrate_pct: RawPct,
    stock_dilutions: StockDilutions | None = None,
    *,
    config: ReleaseGateConfig | None = None,
    concentrate_ul: float = 6000.0,
    repair_pool: RepairPool = None,
    max_passes: int = 4,
    number: int = 1,
    body: str = "",
    family_archetype: str = "",
    rerun_optimizer: RerunCallback | None = None,
) -> GateAwareOptimizationResult:
    """Run gates, repair deterministic failures, and stop on release-ready output.

    Safety failures are repaired by introducing hard raw-uL caps. Missing data,
    forbidden preblends, blocked materials, and brief grammar failures are
    returned as blocked repair actions unless a caller supplies a rerun callback.
    """
    config = config or ReleaseGateConfig()
    stock_dilutions = dict(stock_dilutions or {})
    current = normalize_raw_pct(raw_concentrate_pct)
    actions: list[GateRepairAction] = []
    constraints: dict[str, tuple[float | None, float | None]] = {}
    report: GateReport | None = None
    parent_formula_for_g15: Mapping | None = None

    for pass_index in range(1, max_passes + 1):
        stock_dilutions = _inventory_stock_dilutions(
            tuple(current),
            stock_dilutions,
        )
        formula = raw_pct_to_formula_record(
            name,
            current,
            stock_dilutions,
            concentrate_ul=concentrate_ul,
            number=number,
            body=body,
            family_archetype=family_archetype,
        )
        report = gate_formula(
            formula,
            config,
            parent_formula=parent_formula_for_g15,
        )
        parent_formula_for_g15 = formula
        failed = _failed_gates(report)
        if not failed:
            break

        changed = False
        repaired, new_actions, new_constraints = _apply_ifra_repairs(
            current,
            report,
            stock_dilutions,
            config,
            concentrate_ul=concentrate_ul,
            repair_pool=repair_pool,
            pass_index=pass_index,
        )
        if new_actions:
            current = repaired
            actions.extend(new_actions)
            constraints.update(new_constraints)
            changed = any(action.status == "APPLIED" for action in new_actions)

        if changed:
            continue

        if any(gate.gate == "pipette_floor_neat_traces" for gate in failed):
            repaired, new_actions = _apply_pipette_repairs(
                current,
                stock_dilutions,
                config,
                concentrate_ul=concentrate_ul,
                pass_index=pass_index,
            )
            if new_actions:
                current = repaired
                actions.extend(new_actions)
                changed = changed or any(action.status == "APPLIED" for action in new_actions)

        if changed:
            continue

        if any(gate.gate == "robustness_perturbation" for gate in failed):
            repaired, new_actions, new_constraints = _apply_robustness_repairs(
                current,
                report,
                stock_dilutions,
                config,
                concentrate_ul=concentrate_ul,
                repair_pool=repair_pool,
                pass_index=pass_index,
            )
            if new_actions:
                current = repaired
                actions.extend(new_actions)
                constraints.update(new_constraints)
                changed = changed or any(action.status == "APPLIED" for action in new_actions)

        if changed:
            continue

        blocked = _nonrepairable_actions(report, pass_index)
        if blocked:
            actions.extend(blocked)
            if rerun_optimizer is None:
                break
            current = normalize_raw_pct(rerun_optimizer(constraints, tuple(actions)))
            actions.append(
                GateRepairAction(
                    pass_index=pass_index,
                    gate="optimizer_rerun",
                    action="rerun_optimizer_with_gate_constraints",
                    status="APPLIED",
                    effect="BRIEF_FIT",
                    detail="Caller-supplied optimizer rerun returned a new candidate.",
                )
            )
            continue

        actions.append(
            GateRepairAction(
                pass_index=pass_index,
                gate="repair_loop",
                action="no_repair_available",
                status="BLOCKED",
                effect="BLOCKED",
                detail="Release gates failed but no deterministic repair changed the candidate.",
            )
        )
        break

    stock_dilutions = _inventory_stock_dilutions(tuple(current), stock_dilutions)
    formula = raw_pct_to_formula_record(
        name,
        current,
        stock_dilutions,
        concentrate_ul=concentrate_ul,
        number=number,
        body=body,
        family_archetype=family_archetype,
    )
    final_report = gate_formula(
        formula,
        config,
        parent_formula=parent_formula_for_g15,
    )
    authority = analyze_oav_authority(
        OAVAuthorityRequest(
            formula_name=name,
            ingredients_ul=formula["ingredients_ul"],
            dilutions=formula["dilutions"],
            batch_volume_ml=config.batch_volume_ml,
            temperature_K=config.temperature_K,
            family_archetype=family_archetype,
        )
    )
    unified_scores = compute_unified_release_scores(formula, authority, final_report.as_dict()).as_dict()
    optimizer_report = {
        **final_report.as_dict(),
        "scores": unified_scores["scores"],
        "industry_10": unified_scores["industry_10"],
        "score_provenance": unified_scores["provenance"],
        "oav_table": [
            {
                "name": row.name,
                "dilution": row.dilution,
                "raw_ul": round(row.raw_ul, 2),
                "active_ul": round(row.active_ul, 2),
                "vapor_ppm": round(row.vapor_ppm, 6),
                "odt_air_ppm": row.odt_air_ppm,
                "oav": round(row.oav, 2) if row.oav is not None else None,
                "note": row.note,
            }
            for row in authority.material_rows
        ],
    }
    interventions = build_intervention_contract(
        formula,
        optimizer_report,
        batch_volume_ml=config.batch_volume_ml,
    )
    iterations = pass_index if "pass_index" in locals() else 0
    audit_event_id = None
    if config.audit_enabled:
        event = append_event(
            gate_report_event(
                final_report,
                config,
                event_type="optimize_until_release_ready",
                repair_actions=[action.as_dict() for action in actions],
            )
        )
        audit_event_id = str(event.get("event_id", ""))
    return GateAwareOptimizationResult(
        name=name,
        raw_concentrate_pct=normalize_raw_pct(current),
        gate_report=final_report,
        repair_actions=tuple(actions),
        iterations=iterations,
        interventions=interventions,
        audit_event_id=audit_event_id,
    )


def render_gate_audit_markdown(result: GateAwareOptimizationResult | Mapping) -> list[str]:
    """Render a compact release audit block for optimized formula markdown."""
    payload = result.as_dict() if hasattr(result, "as_dict") else dict(result)
    report = payload.get("gate_report", {})
    confidence = report.get("confidence", {})
    calibration = report.get("calibration_summary", {})
    config = report.get("config_summary", {})
    gates = report.get("gates", [])
    actions = payload.get("repair_actions", [])
    lines = [
        "### Release Gate Audit",
        "",
        f"**Gate status:** `{payload.get('status', report.get('status', 'UNKNOWN'))}`",
        f"**Commercial readiness:** `{payload.get('commercial_readiness', report.get('commercial_readiness', 'UNKNOWN'))}`",
        f"**Family archetype:** `{config.get('family_archetype') or 'not set'}`",
        f"**Commercial mode:** `{config.get('commercial_mode', False)}`",
        f"**Commercial confidence policy:** `{config.get('commercial_confidence_policy', 'block')}`",
        (
            f"**IFRA headroom:** `{float(config.get('effective_ifra_headroom', config.get('ifra_headroom', 1.0))):.0%}` "
            f"(configured `{float(config.get('ifra_headroom', 1.0)):.0%}`)"
        ),
        (
            f"**Audit event:** `{payload.get('audit_event_id') or report.get('audit_event_id') or 'not logged'}`"
        ),
        (
            f"**Confidence:** `{confidence.get('combined_grade', 'UNKNOWN')}` "
            f"({float(confidence.get('combined_confidence', 0.0)):.1f} combined)"
        ),
        "",
    ]
    if calibration:
        lines.extend([
            "### Calibration Summary",
            "",
            (
                f"Records `{calibration.get('formula_records', 0)}`, "
                f"wear observations `{calibration.get('wear_observations', 0)}`, "
                f"panel results `{calibration.get('panel_results', 0)}`, "
                f"ready `{calibration.get('calibration_ready', False)}`"
            ),
            "",
        ])
        intensity_bias = calibration.get("mean_intensity_bias_0_10")
        projection_bias = calibration.get("mean_projection_bias_cm")
        if intensity_bias is not None or projection_bias is not None:
            lines.extend([
                (
                    f"Mean bias: intensity `{intensity_bias if intensity_bias is not None else 'n/a'}`, "
                    f"projection `{projection_bias if projection_bias is not None else 'n/a'} cm`"
                ),
                "",
            ])
    lines.extend([
        "| Gate | Status | Detail |",
        "|---|---:|---|",
    ])

    for gate in gates:
        detail = str(gate.get("detail", "")).replace("|", "/")
        if len(detail) > 180:
            detail = detail[:177] + "..."
        lines.append(f"| {gate.get('gate')} | {gate.get('status')} | {detail or '-'} |")

    lines.extend(["", "### Repair History", ""])
    if actions:
        lines.extend([
            "| Pass | Gate | Action | Material | Change | Effect |",
            "|---:|---|---|---|---:|---|",
        ])
        for action in actions:
            before = action.get("before_ul")
            after = action.get("after_ul")
            change = "-"
            if before is not None or after is not None:
                change = f"{before if before is not None else '-'} -> {after if after is not None else '-'} uL"
            detail = action.get("detail") or action.get("status", "")
            lines.append(
                f"| {action.get('pass_index')} | {action.get('gate')} | "
                f"{action.get('action')} | {action.get('material') or '-'} | "
                f"{change} | {action.get('effect')}: {str(detail).replace('|', '/')} |"
            )
    else:
        lines.append("No repair actions were needed after the optimizer pass.")

    frames = report.get("time_series", [])
    if frames:
        lines.extend(["", "### Gate Time-Series OAV Leaders", ""])
        for frame in frames:
            leaders = frame.get("dominant_oav", [])[:5]
            leader_text = ", ".join(
                f"{row.get('material')} OAV={float(row.get('oav', 0.0)):.1f} ppm={float(row.get('ppm', 0.0)):.6f}"
                for row in leaders
            )
            lines.append(f"- `{frame.get('label')}` ({float(frame.get('t_seconds', 0.0)):.0f}s): {leader_text}")
    lines.append("")
    return lines
