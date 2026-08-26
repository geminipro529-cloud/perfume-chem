"""Formula iteration protocol — codified evaluation timeline and stop criterion.

**RULE 1: All perfume calculations must use ppm, ODT, and OAV.**

Encodes the formula iteration protocol from the Formulation Intelligence Database
(Part XI). Defines the structured timeline for evaluating and modifying a formula:
  - T=0 (Day 0): Skeleton evaluation — adjust RATIOS only
  - T=2 days: Aldehyde-ethanol equilibration — remove/reduce 1-2 worst offenders
  - T=1 week: Early maceration — add 1-2 materials max
  - T=2 weeks: Intermediate maceration — adjust fixative:volatile balance
  - T=4 weeks: First reliable evaluation — trace-level adjustments only
  - T=8 weeks: Secondary maceration — changes < 0.5%
  - T=12 weeks: Final maceration — restart if still needing > 0.5% changes

Includes Roudnitska test (stop criterion) and distance-based evaluation protocol.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from ._shared_types import MACERATION_STAGES, IterationStage

# ---------------------------------------------------------------------------
# Iteration stages
# ---------------------------------------------------------------------------

ITERATION_PROTOCOL: tuple[IterationStage, ...] = (
    IterationStage(
        stage="skeleton_evaluation",
        timepoint_days=0,
        evaluation_focus="Does core accord do what it should? Skeleton evaluation only.",
        allowed_action="Adjust RATIOS only; never fix bad skeleton by adding materials",
    ),
    IterationStage(
        stage="aldehyde_equilibration",
        timepoint_days=2,
        evaluation_focus="Aldehyde-ethanol equilibration begun; rough edge evaluation",
        allowed_action="Remove/reduce 1-2 worst offenders",
    ),
    IterationStage(
        stage="early_maceration",
        timepoint_days=7,
        evaluation_focus="Character completeness check; early coalescence",
        allowed_action="Add 1-2 materials max; never more than 3 per iteration",
    ),
    IterationStage(
        stage="intermediate_maceration",
        timepoint_days=14,
        evaluation_focus="Performance: longevity, projection on blotter and skin",
        allowed_action="Adjust fixative:volatile balance",
    ),
    IterationStage(
        stage="first_reliable_evaluation",
        timepoint_days=28,
        evaluation_focus="First reliable evaluation — evaluate at 4 distances; compare to T=0",
        allowed_action="Trace-level adjustments only (< 1% changes to materials)",
    ),
    IterationStage(
        stage="secondary_maceration",
        timepoint_days=56,
        evaluation_focus="Secondary maceration — final character stable; evaluate at 4 distances",
        allowed_action="Changes < 0.5% formula weight only",
    ),
    IterationStage(
        stage="final_maceration",
        timepoint_days=84,
        evaluation_focus="Final maceration — formula should be complete",
        allowed_action="If still making changes > 0.5%, restart from different skeleton",
    ),
)


# ---------------------------------------------------------------------------
# Evaluation distances
# ---------------------------------------------------------------------------

EVALUATION_DISTANCES: tuple[tuple[str, str, float], ...] = (
    ("close_skin", "Close skin", 3.0),      # 0-5 cm average
    ("personal_zone", "Personal zone", 30.0),  # 20-40 cm
    ("arms_length", "Arm's length", 65.0),      # 50-80 cm
    ("room_entry", "Room entry / ambient", 200.0),  # >150 cm
)


# ---------------------------------------------------------------------------
# Over-dosing strategy table (T=0 → T=4 weeks compensation)
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class OverdoseStrategy:
    """Over-dosing factor for T=0 formulation to hit target at T=4 weeks."""
    material_type: str
    overdose_factor: float     # multiply T=0 dose by this factor
    rationale: str


OVERDOSE_STRATEGIES: tuple[OverdoseStrategy, ...] = (
    OverdoseStrategy(
        "aldehydes (C10, C11, C12 MNA)",
        1.50,
        "Acetal formation over 4 weeks reduces perceived aldehyde intensity; 40-60% excess compensates",
    ),
    OverdoseStrategy(
        "citrus essential oils",
        1.25,
        "Limonene oxidation and acetal equilibration soften the top; 20-30% excess at T=0",
    ),
    OverdoseStrategy(
        "esters (light fruit)",
        1.00,
        "Stable in anhydrous ethanol; no over-dose needed",
    ),
    OverdoseStrategy(
        "benzyl benzoate, sandalwood",
        1.00,
        "Highly stable; dose to target",
    ),
    OverdoseStrategy(
        "coumarin",
        1.10,
        "Mild acetal-like softening over time; 5-10% excess conservative",
    ),
)


# ---------------------------------------------------------------------------
# Accelerated aging
# ---------------------------------------------------------------------------

def accelerated_aging_equivalent(
    real_time_weeks: float,
    real_temp_c: float = 21.0,
    aging_temp_c: float = 50.0,
    q10: float = 2.0,
) -> float:
    """Calculate equivalent accelerated aging time.

    Rule of thumb: 1 week at 50°C ≈ 3 months at 21°C (Q10 = 2.0).

    Args:
        real_time_weeks: real-time duration to simulate
        real_temp_c: real storage temperature (°C)
        aging_temp_c: accelerated aging temperature (°C)
        q10: temperature coefficient

    Returns:
        Accelerated aging time in days
    """
    delta_t = aging_temp_c - real_temp_c
    aat_weeks = real_time_weeks / (q10 ** (delta_t / 10.0))
    return aat_weeks * 7.0  # convert to days


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_stage_by_day(elapsed_days: int) -> IterationStage | None:
    """Return the iteration stage corresponding to elapsed days.

    Returns the most recent stage that should have been completed by this day.
    """
    current: IterationStage | None = None
    for stage in ITERATION_PROTOCOL:
        if elapsed_days >= stage.timepoint_days:
            current = stage
    return current


def get_stage_by_name(stage_name: str) -> IterationStage | None:
    """Return an iteration stage by name."""
    for stage in ITERATION_PROTOCOL:
        if stage.stage == stage_name:
            return stage
    return None


def get_all_stages() -> tuple[IterationStage, ...]:
    """Return all iteration stages in order."""
    return ITERATION_PROTOCOL


def get_next_stage(elapsed_days: int) -> IterationStage | None:
    """Return the next iteration stage that hasn't been reached yet."""
    for stage in ITERATION_PROTOCOL:
        if elapsed_days < stage.timepoint_days:
            return stage
    return None  # all stages completed


def get_evaluation_distances() -> tuple[tuple[str, str, float], ...]:
    """Return the recommended evaluation distance protocol."""
    return EVALUATION_DISTANCES


def get_overdose_strategy(material_type: str) -> OverdoseStrategy | None:
    """Return the over-dosing strategy for a material type at T=0."""
    for strat in OVERDOSE_STRATEGIES:
        if material_type.lower() in strat.material_type.lower():
            return strat
    return None


def roudnitska_test(
    formula_materials: Sequence[str],
    evaluation_function,  # callable: (materials_without_mat) → score
) -> tuple[bool, list[str]]:
    """Apply the Roudnitska stop criterion.

    The formula is finished when removing ANY material makes it worse —
    NOT when adding anything fails to improve it.

    Args:
        formula_materials: list of material names in the formula
        evaluation_function: function that scores a list of materials
            (should return a numeric score where higher is better)

    Returns:
        (is_finished, list of materials whose removal improved the formula)
    """
    base_score = evaluation_function(list(formula_materials))
    improvements = []

    for mat in formula_materials:
        reduced = [m for m in formula_materials if m != mat]
        try:
            reduced_score = evaluation_function(reduced)
            if reduced_score > base_score:
                improvements.append(mat)
        except Exception:
            continue

    return len(improvements) == 0, improvements


def format_iteration_status(elapsed_days: int) -> str:
    """Return a human-readable status for the current iteration stage."""
    current = get_stage_by_day(elapsed_days)
    next_stage = get_next_stage(elapsed_days)

    if current is None:
        return "Pre-T=0: formula skeleton not yet evaluated"

    msg = f"Day {elapsed_days} — {current.stage.replace('_', ' ').title()}: {current.evaluation_focus}"
    if next_stage:
        days_to_next = next_stage.timepoint_days - elapsed_days
        msg += f"\n  Next stage in {days_to_next} day(s): {next_stage.stage.replace('_', ' ').title()}"
    else:
        msg += "\n  All stages complete — formula ready for final evaluation"
    return msg


def get_maceration_milestone(elapsed_days: int) -> str:
    """Return the maceration milestone closest to the elapsed time."""
    milestones = sorted(MACERATION_STAGES.items(), key=lambda x: x[1])
    closest = milestones[0]
    for name, days in milestones:
        if elapsed_days >= days:
            closest = (name, days)
    return f"{closest[0].replace('_', ' ').title()} ({closest[1]} days)"


def evaluate_stage_compliance(
    elapsed_days: int,
    changes_made: int,
    largest_change_pct: float,
) -> tuple[bool, str]:
    """Check if recent formula modifications comply with the iteration protocol.

    Args:
        elapsed_days: days since formula creation
        changes_made: number of materials modified in this iteration
        largest_change_pct: the largest % change to any single material

    Returns:
        (is_compliant, explanation)
    """
    current = get_stage_by_day(elapsed_days)
    if current is None:
        return True, "Pre-T=0: no constraints yet"

    # Parse the allowed action for constraints
    if "never fix bad skeleton by adding materials" in current.allowed_action:
        if changes_made > 0:
            return False, "T=0 day: adjust RATIOS only, don't add/remove materials"
        return True, "Ratios only at T=0"

    if "remove/reduce 1-2 worst offenders" in current.allowed_action:
        if changes_made > 2:
            return False, f"Day {elapsed_days}: max 2 materials can be modified; {changes_made} attempted"
        return True, "Within 2-material limit"

    if "add 1-2 materials max" in current.allowed_action:
        if changes_made > 2:
            return False, f"Day {elapsed_days}: max 2 materials can be added; {changes_made} attempted"
        return True, "Within 2-material addition limit"

    if "adjust fixative:volatile balance" in current.allowed_action:
        return True, "Fixative:volatile adjustment allowed"

    if "trace-level adjustments only" in current.allowed_action:
        if largest_change_pct > 1.0:
            return False, f"Day {elapsed_days}: max 1% changes allowed; {largest_change_pct}% attempted"
        return True, "Within trace-level adjustment limit"

    if "changes < 0.5% formula weight only" in current.allowed_action:
        if largest_change_pct > 0.5:
            return False, f"Day {elapsed_days}: max 0.5% changes allowed; {largest_change_pct}% attempted"
        return True, "Within 0.5% adjustment limit"

    return True, "Stage compliance ok"
