"""Professional evaluation protocol — blotter, skin, 5-distance grid, fatigue management.

**RULE 1: All perfume calculations must use ppm, ODT, and OAV.**

Encodes the professional evaluation intelligence from the Advanced Perfumery
Supplement (Gaps 5 + 15). The 5-distance grid replaces the previous 4-distance
protocol. Covers:

  - Blotter (mouillette) evaluation schedule
  - The "next morning test"
  - Olfactory fatigue management (coffee bean myth, true receptor reset)
  - 5-distance professional evaluation grid
  - Skin application locations and pulse point hierarchy
  - Spray technique and skin preparation
  - The "never apply two formulas to same skin area" rule
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


# ---------------------------------------------------------------------------
# Blotter evaluation schedule
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class BlotterEvaluationPoint:
    """One timepoint in the professional blotter evaluation protocol."""
    timepoint: str
    elapsed: str              # human-readable elapsed time
    evaluation_focus: str
    action: str


BLOTTER_SCHEDULE: tuple[BlotterEvaluationPoint, ...] = (
    BlotterEvaluationPoint(
        "T=0 (wet)", "Immediately after dipping",
        "First impression, top note character, any immediate off-notes",
        "Never make formula decisions based on this — alcohol dominates perception",
    ),
    BlotterEvaluationPoint(
        "T=10 seconds", "After air-drying",
        "Top note 'true' character — alcohol evaporates, true materials emerge",
        "Primary character identification — this is the most important top-note timepoint",
    ),
    BlotterEvaluationPoint(
        "T=5 min", "5 minutes",
        "Heart notes beginning to register; transition quality",
        "Is there an 'olfactory cliff' between top and heart?",
    ),
    BlotterEvaluationPoint(
        "T=20 min", "20 minutes",
        "Full heart note development",
        "Primary hedonic evaluation of character — is it beautiful?",
    ),
    BlotterEvaluationPoint(
        "T=2-4 hours", "2 to 4 hours",
        "Heart-to-base transition",
        "Dry-down character — does it become more beautiful over time?",
    ),
    BlotterEvaluationPoint(
        "T=8-24 hours", "Next morning (8-24 hours)",
        "Base note and fixative — the 'next morning test'",
        "What remains on blotter the next morning? Smell as first smell of the day before coffee/food.",
    ),
    BlotterEvaluationPoint(
        "T=48 hours", "48 hours",
        "Ultra-base — musks, resins",
        "True material longevity. Musks and benzyl benzoate should still be faintly present.",
    ),
)


# ---------------------------------------------------------------------------
# Olfactory fatigue management
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class FatigueRule:
    """One rule for managing olfactory fatigue during evaluation."""
    topic: str
    truth: str
    myth: str | None = None


FATIGUE_RULES: tuple[FatigueRule, ...] = (
    FatigueRule(
        "3-material limit",
        "After 3 consecutive materials, the receptors partially adapt. Take a 5-minute break or smell your own neutral skin (inner elbow).",
    ),
    FatigueRule(
        "Coffee bean reset",
        "Coffee beans do NOT reset olfactory receptors. They provide a complex competing odor that can 'override' the previous olfactory memory, but this is psychological/memory-clearing, not receptor reset. The same effect occurs with one's own neutral skin.",
        "MYTH: Coffee beans reset olfactory receptors.",
    ),
    FatigueRule(
        "True receptor reset",
        "Fresh outdoor air, 20 minutes. All other 'resets' are psychological/memory-clearing only.",
    ),
    FatigueRule(
        "Session timing",
        "Evaluate only before meals, not after. Highest olfactory sensitivity: 10-11 AM and 4-5 PM. Lowest: immediately after waking, during digestion, during illness.",
    ),
    FatigueRule(
        "Next morning test",
        "Professional perfumers leave labeled blotters overnight and smell them the next morning as the first smell of the day (before coffee/food). This eliminates olfactory adaptation that occurs during the work session.",
    ),
)


# ---------------------------------------------------------------------------
# 5-Distance Professional Evaluation Grid (Gap 15)
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class DistanceZone:
    """One evaluation distance zone in the 5-distance professional grid."""
    distance_cm: tuple[float, float]
    zone_name: str
    evaluation_focus: str
    material_oav_requirement: str


FIVE_DISTANCE_GRID: tuple[DistanceZone, ...] = (
    DistanceZone(
        (0, 5), "Intimate skin-read",
        "True base character; what you smell when embracing",
        "Requires OAV > 2 on skin at 4+ hours",
    ),
    DistanceZone(
        (5, 20), "Personal space",
        "Day-3 dry-down character; long-term longevity",
        "Requires OAV > 1 at 6 hours",
    ),
    DistanceZone(
        (20, 50), "Personal projection",
        "Normal conversation distance character",
        "Heart note must dominate this zone",
    ),
    DistanceZone(
        (50, 150), "Sillage",
        "The 'trail' character — what follows you",
        "Mid-VP materials OAV > 5 (Hedione, Iso E Super zone)",
    ),
    DistanceZone(
        (150, 999), "Room entry",
        "Can the fragrance be smelled as you enter a room?",
        "Only highest-diffusion materials: Hedione HC, high-dose Ambroxan, Aldehydes",
    ),
)


# ---------------------------------------------------------------------------
# Skin application protocol
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class SkinApplicationPoint:
    """A body location for fragrance application and its evaluation properties."""
    location: str
    why_use: str
    best_for: str
    blood_flow: str


SKIN_APPLICATION_POINTS: tuple[SkinApplicationPoint, ...] = (
    SkinApplicationPoint(
        "Inner wrist", "Most standard — high blood flow, visible, accessible",
        "General character evaluation", "High",
    ),
    SkinApplicationPoint(
        "Inner elbow", "Less contamination from hand contact, good for long-term evaluation",
        "Heart/base evaluation", "Moderate",
    ),
    SkinApplicationPoint(
        "Neck / behind ear", "Warmest skin location, highest diffusion, traditional pulse point",
        "Sillage and projection evaluation", "Very high",
    ),
    SkinApplicationPoint(
        "Back of hand", "Closest to body temperature average, dry area, minimal interference",
        "True dry-down character", "Moderate",
    ),
    SkinApplicationPoint(
        "Forearm (inner)", "Large surface area suitable for side-by-side comparison",
        "Comparing two formulas at once (on opposite arms ONLY)", "Moderate",
    ),
)


# ---------------------------------------------------------------------------
# Application rules
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ApplicationRule:
    """One professional application rule."""
    rule: str
    rationale: str


APPLICATION_RULES: tuple[ApplicationRule, ...] = (
    ApplicationRule(
        "Never apply two different formulas to the same skin area",
        "OAV interference between two formulas read simultaneously is 3-5× suppression — you are not evaluating either formula accurately.",
    ),
    ApplicationRule(
        "Hold bottle 15-20 cm from skin; don't rub",
        "Rubbing destroys top note structure by heat and mechanical disruption. The friction heat accelerates evaporation and the mechanical action crushes fragrance micro-droplets.",
    ),
    ApplicationRule(
        "Unscented moisturizer 30 minutes before application",
        "Significantly increases longevity for dry skin — the hydrating lipid layer enhances logP 3-5 material depot.",
    ),
    ApplicationRule(
        "Pulse point hierarchy: Neck > inner wrist > inner elbow > chest",
        "For maximum projection: apply to neck. For longevity: apply to inner elbows (less air exposure). For intimate: chest/sternum.",
    ),
    ApplicationRule(
        "Wait 60 seconds before evaluating skin application",
        "The alcohol evaporation phase creates a different olfactory impression from the true skin-dry character. Wait for alcohol to fully evaporate.",
    ),
)


# ---------------------------------------------------------------------------
# Sephora-house level criteria (5-distance rule)
# ---------------------------------------------------------------------------

FIVE_DISTANCE_RULE: str = (
    "A perfume formulated for Sephora-house level must have distinct character "
    "at every distance without being overwhelming at any distance. "
    "A weak intimate-skin layer signals cheap materials or under-fixation. "
    "An overwhelming room-entry signal indicates an over-dosed formula."
)


DOWNGRADE_INDICATORS: tuple[tuple[str, str], ...] = (
    ("Weak intimate skin layer", "Signals cheap materials or under-fixation — premium formulas have a luxurious skin-close experience"),
    ("Overwhelming room entry", "Indicates over-dosed formula — may be impressive but reads as 'loud' not 'luxurious'"),
    ("No heart note at personal distance", "The 'conversation distance' gap — formula has top but no meaningful heart development"),
    ("Rapid base fade", "Base materials too volatile or under-loaded — luxury formulas persist at intimate distance 12+ hours"),
    ("Olfactory cliff between zones", "Abrupt character change between distances — smooth transition is the hallmark of luxury blends"),
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_blotter_schedule() -> tuple[BlotterEvaluationPoint, ...]:
    """Return the complete blotter evaluation schedule."""
    return BLOTTER_SCHEDULE


def get_fatigue_rules() -> tuple[FatigueRule, ...]:
    """Return olfactory fatigue management rules."""
    return FATIGUE_RULES


def get_five_distance_grid() -> tuple[DistanceZone, ...]:
    """Return the 5-distance professional evaluation grid."""
    return FIVE_DISTANCE_GRID


def get_zone_by_distance(distance_cm: float) -> DistanceZone | None:
    """Return the evaluation zone for a given distance from skin."""
    for zone in FIVE_DISTANCE_GRID:
        if zone.distance_cm[0] <= distance_cm <= zone.distance_cm[1]:
            return zone
    return None


def get_skin_application_points() -> tuple[SkinApplicationPoint, ...]:
    """Return the skin application location guide."""
    return SKIN_APPLICATION_POINTS


def get_application_rules() -> tuple[ApplicationRule, ...]:
    """Return professional application rules."""
    return APPLICATION_RULES


def evaluate_sephora_house_level(
    intimate_layer_present: bool,
    room_entry_not_overwhelming: bool,
    heart_at_personal_distance: bool,
    base_persists_12h: bool,
    smooth_zone_transitions: bool,
) -> tuple[float, str]:
    """Score a formula against Sephora-house level criteria.

    Returns:
        (score 0-1, diagnostic message)
    """
    checks = {
        "intimate_layer": intimate_layer_present,
        "room_entry_controlled": room_entry_not_overwhelming,
        "heart_at_personal": heart_at_personal_distance,
        "base_persists": base_persists_12h,
        "smooth_transitions": smooth_zone_transitions,
    }
    score = sum(checks.values()) / len(checks)

    failures = [k for k, v in checks.items() if not v]
    if not failures:
        return score, "Meets Sephora-house level criteria at all 5 distances"
    if score >= 0.6:
        return score, f"Near Sephora-house level — improve: {', '.join(failures)}"
    return score, f"Below Sephora-house level — critical gaps: {', '.join(failures)}"


def get_downgrade_indicators() -> tuple[tuple[str, str], ...]:
    """Return indicators that a formula falls below Sephora-house quality."""
    return DOWNGRADE_INDICATORS


def format_blotter_timeline() -> str:
    """Return a human-readable blotter evaluation timeline."""
    lines = []
    for bp in BLOTTER_SCHEDULE:
        lines.append(f"{bp.timepoint} ({bp.elapsed}): {bp.evaluation_focus}")
        lines.append(f"  → {bp.action}")
    return "\n".join(lines)
