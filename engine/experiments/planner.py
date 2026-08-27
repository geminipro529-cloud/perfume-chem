"""Information-gain experiment planner.

Designs experiments that maximise learning per unit cost/risk.
"""

from __future__ import annotations

import random
import string
import uuid
from dataclasses import asdict, dataclass
from typing import Any


# ── ExperimentPlan dataclass ─────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class ExperimentPlan:
    """A designed experiment with estimated cost, risk, and information gain.

    Parameters
    ----------
    plan_id : str
        UUID string uniquely identifying this plan.
    description : str
        Human-readable description of the experiment.
    variant_count : int
        Number of variants (aliquots) to prepare.
    estimated_cost_ul : float
        Estimated total material cost in microlitres.
    estimated_time_minutes : int
        Estimated total time for preparation and evaluation.
    irreversibility : float
        How hard the experiment is to undo, from 0 (fully reversible) to
        1 (irreversible).
    expected_information_gain : float
        Expected learning yield, from 0 (nothing new) to 1 (definitive
        answer).
    expected_sensory_value : float
        Expected sensory value of the result, from 0 (useless) to 1
        (highly informative to the nose).
    utility_score : float
        Computed utility from ``compute_utility``.
    instructions : tuple[str, ...]
        Step-by-step instructions for executing the experiment.
    """

    plan_id: str
    description: str
    variant_count: int = 1
    estimated_cost_ul: float = 0.0
    estimated_time_minutes: int = 30
    irreversibility: float = 0.0
    expected_information_gain: float = 0.0
    expected_sensory_value: float = 0.0
    utility_score: float = 0.0
    instructions: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


# ── Utility computation ──────────────────────────────────────────────────────


def compute_utility(
    gain: float,
    sensory: float,
    cost_ul: float,
    irreversibility: float,
    time_min: int,
) -> float:
    """Compute experiment utility from information gain, sensory value, and cost.

    Utility = (gain * sensory) / (max(cost_ul, 1) * max(irreversibility, 0.1) * max(time_min, 5))

    Parameters
    ----------
    gain : float
        Expected information gain (0-1).
    sensory : float
        Expected sensory value (0-1).
    cost_ul : float
        Estimated material cost in microlitres.
    irreversibility : float
        How hard to undo (0-1).
    time_min : int
        Estimated time in minutes.

    Returns
    -------
    float
        Computed utility score.
    """
    denominator = max(cost_ul, 1.0) * max(irreversibility, 0.1) * max(time_min, 5)
    return (gain * sensory) / denominator


# ── Helpers ──────────────────────────────────────────────────────────────────


def _random_code(length: int = 3) -> str:
    """Generate a random uppercase letter code of the given length."""
    return "".join(random.choices(string.ascii_uppercase, k=length))


def _default_time_points() -> tuple[str, ...]:
    return ("0 min (immediate)", "5 min", "30 min", "120 min")


# ── Omission test ────────────────────────────────────────────────────────────


def suggest_omission_test(formula_materials: list[dict]) -> ExperimentPlan:
    """Design a coded omission test for character/signature materials.

    Each material dict should have keys ``name``, ``role``, and ``dose_ul``.
    Materials with role ``"character"`` or ``"signature"`` are individually
    omitted (replaced with DPG) in separate coded aliquots.

    Parameters
    ----------
    formula_materials : list[dict]
        List of material dicts with at least ``name``, ``role``, ``dose_ul``.

    Returns
    -------
    ExperimentPlan
        A plan with instructions for preparing and evaluating the omission
        test.
    """
    character_materials = [
        m for m in formula_materials if m.get("role") in ("character", "signature")
    ]

    if not character_materials:
        return ExperimentPlan(
            plan_id=str(uuid.uuid4()),
            description="Omission test — no character/signature materials found",
            variant_count=0,
            estimated_cost_ul=0.0,
            estimated_time_minutes=0,
            irreversibility=0.0,
            expected_information_gain=0.0,
            expected_sensory_value=0.0,
            utility_score=0.0,
            instructions=("No character or signature materials to test.",),
        )

    variant_count = len(character_materials) + 1  # +1 for the full reference
    total_cost = sum(m.get("dose_ul", 0) for m in character_materials)
    codes: list[str] = []
    instructions: list[str] = [
        f"Omission test: {len(character_materials)} character material(s)",
        "",
        "Prepare the following coded aliquots:",
    ]

    # Full reference (all materials present)
    ref_code = _random_code()
    codes.append(ref_code)
    instructions.append(f"  {ref_code} — Full formula (reference)")

    # One omission per character material
    for mat in character_materials:
        code = _random_code()
        codes.append(code)
        instructions.append(
            f"  {code} — Omit {mat['name']} ({mat['dose_ul']} uL), replace with DPG"
        )

    instructions.append("")
    instructions.append("Evaluation protocol:")
    for tp in _default_time_points():
        instructions.append(f"  - Evaluate at {tp}")
    instructions.append("")
    instructions.append(
        "Record perceived difference from reference for each variant "
        "at each time point. Note whether the omitted material is "
        "detectable in the full formula."
    )

    gain = min(0.5 + 0.1 * len(character_materials), 0.95)
    sensory = 0.7
    irreversibility = 0.3  # can always add back
    time_min = 30 + 15 * variant_count

    utility = compute_utility(
        gain=gain,
        sensory=sensory,
        cost_ul=float(total_cost),
        irreversibility=irreversibility,
        time_min=time_min,
    )

    return ExperimentPlan(
        plan_id=str(uuid.uuid4()),
        description=f"Omission test: {len(character_materials)} character material(s)",
        variant_count=variant_count,
        estimated_cost_ul=float(total_cost),
        estimated_time_minutes=time_min,
        irreversibility=irreversibility,
        expected_information_gain=gain,
        expected_sensory_value=sensory,
        utility_score=utility,
        instructions=tuple(instructions),
    )


# ── Addition range ───────────────────────────────────────────────────────────


def suggest_addition_range(material: str, center_dose_ul: float) -> ExperimentPlan:
    """Design a low/center/high dose experiment for a single material.

    Parameters
    ----------
    material : str
        Name of the material to test.
    center_dose_ul : float
        Centre-point dose in microlitres.

    Returns
    -------
    ExperimentPlan
        A plan with three coded aliquots at 50%, 100%, and 150% of centre.
    """
    low = center_dose_ul * 0.5
    center = center_dose_ul
    high = center_dose_ul * 1.5

    codes = [_random_code(), _random_code(), _random_code()]
    total_cost = low + center + high

    instructions: list[str] = [
        f"Addition range test: {material}",
        "",
        "Prepare the following coded aliquots:",
        f"  {codes[0]} — {material} at {low:.1f} uL (50% of centre)",
        f"  {codes[1]} — {material} at {center:.1f} uL (centre)",
        f"  {codes[2]} — {material} at {high:.1f} uL (150% of centre)",
        "",
        "Evaluation protocol:",
    ]
    for tp in _default_time_points():
        instructions.append(f"  - Evaluate at {tp}")
    instructions.append("")
    instructions.append(
        "Record perceived intensity, character change, and balance "
        "impact for each dose. Note the threshold where the material "
        "becomes dominant or disruptive."
    )

    gain = 0.6  # dose-response is informative but not definitive
    sensory = 0.8  # directly perceptible
    irreversibility = 0.2  # low — can dilute further
    time_min = 45

    utility = compute_utility(
        gain=gain,
        sensory=sensory,
        cost_ul=total_cost,
        irreversibility=irreversibility,
        time_min=time_min,
    )

    return ExperimentPlan(
        plan_id=str(uuid.uuid4()),
        description=f"Addition range: {material} ({low:.0f}-{high:.0f} uL)",
        variant_count=3,
        estimated_cost_ul=total_cost,
        estimated_time_minutes=time_min,
        irreversibility=irreversibility,
        expected_information_gain=gain,
        expected_sensory_value=sensory,
        utility_score=utility,
        instructions=tuple(instructions),
    )


# ── Blind trial ──────────────────────────────────────────────────────────────


def design_blind_trial(samples: list[dict]) -> ExperimentPlan:
    """Design a blind trial comparing multiple samples.

    Each sample dict should have keys ``label`` and ``formula`` (a
    descriptive string). Random 3-letter codes are assigned to each
    sample.

    Parameters
    ----------
    samples : list[dict]
        List of sample dicts with at least ``label`` and ``formula``.

    Returns
    -------
    ExperimentPlan
        A plan with coded evaluation instructions.
    """
    if not samples:
        return ExperimentPlan(
            plan_id=str(uuid.uuid4()),
            description="Blind trial — no samples provided",
            variant_count=0,
            estimated_cost_ul=0.0,
            estimated_time_minutes=0,
            irreversibility=0.0,
            expected_information_gain=0.0,
            expected_sensory_value=0.0,
            utility_score=0.0,
            instructions=("No samples to evaluate.",),
        )

    codes: list[str] = []
    instructions: list[str] = [
        "Blind trial — coded evaluation",
        "",
        "Samples:",
    ]

    for s in samples:
        code = _random_code()
        codes.append(code)
        instructions.append(f"  {code} — {s.get('label', 'Unnamed')}")

    instructions.append("")
    instructions.append("Reference standard (if available):")
    instructions.append("  Compare each coded sample against the reference.")
    instructions.append("")
    instructions.append("Evaluation protocol:")
    for tp in _default_time_points():
        instructions.append(f"  - Evaluate at {tp}")
    instructions.append("")
    instructions.append("For each coded sample at each time point, record:")
    instructions.append("  - Perceived intensity (0-10)")
    instructions.append("  - Character description (3-5 keywords)")
    instructions.append("  - Similarity to reference (0-10)")
    instructions.append("  - Preference ranking across all samples")

    variant_count = len(samples)
    gain = 0.7
    sensory = 0.9
    irreversibility = 0.1  # purely observational
    time_min = 20 * variant_count

    utility = compute_utility(
        gain=gain,
        sensory=sensory,
        cost_ul=0.0,  # no material cost for evaluation
        irreversibility=irreversibility,
        time_min=time_min,
    )

    return ExperimentPlan(
        plan_id=str(uuid.uuid4()),
        description=f"Blind trial: {variant_count} sample(s)",
        variant_count=variant_count,
        estimated_cost_ul=0.0,
        estimated_time_minutes=time_min,
        irreversibility=irreversibility,
        expected_information_gain=gain,
        expected_sensory_value=sensory,
        utility_score=utility,
        instructions=tuple(instructions),
    )


# ── Material pair test ───────────────────────────────────────────────────────


def suggest_material_pair_test(
    material_a: str,
    material_b: str,
    dose_a: float,
    dose_b: float,
) -> ExperimentPlan:
    """Design a 2x2 material pair test to reveal synergy or masking.

    Tests four combinations: neither, A only, B only, both. This answers
    the key question: "Do these two materials belong together?"

    Parameters
    ----------
    material_a : str
        Name of the first material.
    material_b : str
        Name of the second material.
    dose_a : float
        Dose of material A in microlitres.
    dose_b : float
        Dose of material B in microlitres.

    Returns
    -------
    ExperimentPlan
        A plan with four coded aliquots.
    """
    codes = [_random_code(), _random_code(), _random_code(), _random_code()]
    total_cost = dose_a + dose_b

    instructions: list[str] = [
        f"Material pair test: {material_a} x {material_b}",
        "",
        "Prepare the following coded aliquots (in a neutral base):",
        f"  {codes[0]} — Neither (blank / base only)",
        f"  {codes[1]} — {material_a} only ({dose_a:.1f} uL)",
        f"  {codes[2]} — {material_b} only ({dose_b:.1f} uL)",
        f"  {codes[3]} — Both ({material_a} {dose_a:.1f} uL + {material_b} {dose_b:.1f} uL)",
        "",
        "Evaluation protocol:",
    ]
    for tp in _default_time_points():
        instructions.append(f"  - Evaluate at {tp}")
    instructions.append("")
    instructions.append("For each coded sample at each time point, record:")
    instructions.append("  - Perceived intensity (0-10)")
    instructions.append("  - Character description")
    instructions.append("  - Is the combination synergistic, masking, or additive?")
    instructions.append("  - Does one material dominate the other?")
    instructions.append("")
    instructions.append(
        "Key question: Do these two materials belong together in the same composition?"
    )

    # Pair tests have high utility — they answer a fundamental question.
    gain = 0.85
    sensory = 0.9
    irreversibility = 0.2
    time_min = 60

    utility = compute_utility(
        gain=gain,
        sensory=sensory,
        cost_ul=total_cost,
        irreversibility=irreversibility,
        time_min=time_min,
    )

    return ExperimentPlan(
        plan_id=str(uuid.uuid4()),
        description=f"Pair test: {material_a} x {material_b}",
        variant_count=4,
        estimated_cost_ul=total_cost,
        estimated_time_minutes=time_min,
        irreversibility=irreversibility,
        expected_information_gain=gain,
        expected_sensory_value=sensory,
        utility_score=utility,
        instructions=tuple(instructions),
    )


__all__ = [
    "ExperimentPlan",
    "compute_utility",
    "design_blind_trial",
    "suggest_addition_range",
    "suggest_material_pair_test",
    "suggest_omission_test",
]
