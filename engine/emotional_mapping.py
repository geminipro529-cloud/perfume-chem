"""Quarantined hypotheses for odor-associated mood language.

The material labels below are legacy, hand-authored priors for designing a
human self-report study. They are not measurements of a formula, do not infer
neurotransmitter release, and have no release or dosing authority. Odor
valence depends substantially on person, context, culture, learning, label,
mixture interactions, and exposure. A report remains UNKNOWN until a
pre-registered blinded psychophysical protocol supplies formula-specific
observations.
"""

from __future__ import annotations

from dataclasses import dataclass

from engine.material_data_loader import load_engine_data as _load_engine_data

# ═══════════════════════════════════════════════════════════════════════════════
# Legacy hypothesis-prior data. The numbers are not validated measurements and
# must never be emitted as formula truth or used as a release gate.
# ═══════════════════════════════════════════════════════════════════════════════

EMOTIONAL_PROFILES = _load_engine_data("emotional_mapping", "EMOTIONAL_PROFILES")


# ═══════════════════════════════════════════════════════════════════════════════
# Scoring
# ═══════════════════════════════════════════════════════════════════════════════

MOOD_DIMS = ["calming", "energizing", "sensual", "comforting", "grounding", "uplifting"]


@dataclass
class EmotionalReport:
    """Evidence-bounded emotional-association report."""
    score: float | None
    mood_vector: dict[str, float]
    dominant_mood: str
    secondary_mood: str
    emotional_narrative: str
    coherence: float | None
    ambiguity: float | None
    diagnostics: list[str]
    status: str = "UNKNOWN"
    evidence_class: str = "HYPOTHESIS_PRIOR_ONLY"
    release_authority: bool = False


def _legacy_score_emotional_unvalidated(
    ingredients: dict[str, float],
    dilutions: dict[str, float] | None = None,
) -> EmotionalReport:
    """Retained research prototype; never call from release or dosing paths.

    This deterministic arithmetic has no held-out human validation. Keeping it
    private preserves the historical experiment while preventing accidental
    promotion to formula truth.
    """
    dilutions = dilutions or {}
    total_active = 0.0
    mood_accum = {d: 0.0 for d in MOOD_DIMS}
    diagnostics: list[str] = []
    profiled_mass = 0.0

    for name, amount in ingredients.items():
        dil = dilutions.get(name, 1.0)
        active = amount * dil
        total_active += active

        profile = EMOTIONAL_PROFILES.get(name)
        if not profile:
            continue

        profiled_mass += active
        for dim in MOOD_DIMS:
            mood_accum[dim] += profile.get(dim, 0.0) * active

    if total_active == 0 or profiled_mass == 0:
        return EmotionalReport(
            score=50, mood_vector={d: 0 for d in MOOD_DIMS},
            dominant_mood="none", secondary_mood="none",
            emotional_narrative="Insufficient data for emotional mapping",
            coherence=0, ambiguity=0, diagnostics=["No emotional data"],
        )

    # Normalize mood vector
    mood_vec = {d: mood_accum[d] / profiled_mass for d in MOOD_DIMS}

    # Sorted moods
    sorted_moods = sorted(mood_vec.items(), key=lambda x: x[1], reverse=True)
    dominant = sorted_moods[0][0]
    secondary = sorted_moods[1][0]
    dom_val = sorted_moods[0][1]
    sec_val = sorted_moods[1][1]

    # Coherence: dominant mood's share of total mood signal
    total_signal = sum(mood_vec.values())
    coherence = dom_val / total_signal if total_signal > 0 else 0.0

    # Ambiguity: opposing moods in tension
    # calming ↔ energizing, comforting ↔ energizing
    opposing_pairs = [("calming", "energizing"), ("comforting", "energizing")]
    ambiguity = 0.0
    for a, b in opposing_pairs:
        if mood_vec[a] > 0.15 and mood_vec[b] > 0.15:
            ambiguity += min(mood_vec[a], mood_vec[b]) * 2

    ambiguity = min(1.0, ambiguity)

    # Narrative
    narrative_map = {
        "calming": "serene and meditative",
        "energizing": "vibrant and invigorating",
        "sensual": "intimate and seductive",
        "comforting": "warm and nurturing",
        "grounding": "stable and contemplative",
        "uplifting": "joyful and euphoric",
    }
    if sec_val > dom_val * 0.6:
        narrative = f"{narrative_map[dominant]} with {narrative_map[secondary]} undertones"
    else:
        narrative = narrative_map[dominant]

    # Score: reward clear emotional story
    base = coherence * 60 + 30  # 30-90 base
    ambiguity_penalty = ambiguity * 20
    score = base - ambiguity_penalty
    # Bonus for strong dominant mood
    if dom_val > 0.5:
        score += 10
    score = max(0, min(100, score))

    # Diagnostics
    diagnostics.append(f"Emotional narrative: {narrative}")
    diagnostics.append(
        f"Mood vector: {', '.join(f'{d}={v:.2f}' for d, v in sorted_moods)}"
    )
    if ambiguity > 0.3:
        diagnostics.append(
            "⚠ Emotional ambiguity — conflicting mood signals "
            "(may be intentional artistic choice)"
        )
    if coherence > 0.4:
        diagnostics.append("✓ Clear emotional identity")

    return EmotionalReport(
        score=round(score, 1),
        mood_vector={d: round(v, 3) for d, v in mood_vec.items()},
        dominant_mood=dominant,
        secondary_mood=secondary,
        emotional_narrative=narrative,
        coherence=round(coherence, 3),
        ambiguity=round(ambiguity, 3),
        diagnostics=diagnostics,
    )


def score_emotional(
    ingredients: dict[str, float],
    dilutions: dict[str, float] | None = None,
) -> EmotionalReport:
    """Return UNKNOWN until formula-specific human observations are supplied."""
    del dilutions
    hypothesis_matches = sorted(
        name for name in ingredients if name in EMOTIONAL_PROFILES
    )
    return EmotionalReport(
        score=None,
        mood_vector={},
        dominant_mood="unknown",
        secondary_mood="unknown",
        emotional_narrative=(
            "No formula-specific blinded self-report evidence is available."
        ),
        coherence=None,
        ambiguity=None,
        diagnostics=[
            f"Legacy hypothesis matches: {len(hypothesis_matches)}",
            (
                "Required evidence: randomized blinded ratings with context, "
                "label, dose, and participant provenance."
            ),
            (
                "Brain imaging or receptor activity must not be relabeled as "
                "neurotransmitter release or consumer emotion."
            ),
        ],
    )
