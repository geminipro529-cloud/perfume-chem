"""Chemical life graph — per-formula diagnostic & compatibility analysis.

For every perfume formula, generates a comprehensive diagnostic that shows:
  1. Which musks work with the formula's wood/floral base
  2. What material stacks synergize
  3. What is too heavy (overweight character dimensions)
  4. Which structural gaps need filling (missing roles, textures, notes)
  5. Temporal evolution — how the formula changes over time

This is the "health report" for a perfume formula. Think of it as a
clinical data panel: the formula's vitals, imbalances, and opportunities.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from engine.fingerprint import (
    FormulaFingerprint,
    fingerprint_formula,
)
from engine.ingredient_intelligence import (
    DIMENSIONS,
    get_all_profiles,
    get_profile,
)
from engine.synergy_graph import (
    MuskCompatibility,
    SynergyGraph,
    SynergyStack,
)
from engine.volatility import VolatilityCurveSimulator

# ═══════════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class WeightDiagnosis:
    """Identifies overweight and underweight character dimensions."""
    overweight: list[tuple[str, float]]    # (dimension, excess above target)
    underweight: list[tuple[str, float]]   # (dimension, deficit below target)
    balance_score: float                   # 0-100, higher = more balanced

    @property
    def heaviest_dimension(self) -> str | None:
        return self.overweight[0][0] if self.overweight else None

    @property
    def lightest_dimension(self) -> str | None:
        return self.underweight[0][0] if self.underweight else None


@dataclass
class StructuralGap:
    """A missing structural element in the formula."""
    gap_type: str          # "role", "note", "texture", "dimension"
    name: str              # what's missing
    severity: float        # 0-1
    suggestion: str        # what to add
    candidates: list[str]  # inventory materials that could fill the gap


@dataclass
class SynergyReport:
    """Synergy analysis within the formula."""
    overall_synergy: float          # -1 to +1
    strongest_pairs: list[tuple[str, str, float]]
    weakest_pairs: list[tuple[str, str, float]]
    clash_pairs: list[tuple[str, str, float]]
    stacks: list[SynergyStack]


@dataclass
class TemporalProfile:
    """Uncalibrated temporal-structure diagnostics.

    Model windows describe relative compositional evolution only. They are not
    measured blotter or skin times and cannot support a longevity claim.
    """
    note_transitions: list[dict[str, Any]]  # when top→heart→base shifts occur
    longevity_hours: None
    top_dominance_model_minutes: float
    base_dominance_model_hours: float | None
    linear_score: float
    authority: str
    release_authority: bool


@dataclass
class ChemicalLifeGraph:
    """Complete diagnostic for a single formula."""
    formula_name: str
    structure_mode: str
    ingredient_count: int
    total_mass_ul: float
    concentrate_pct: float

    # Fingerprint summary
    fingerprint: FormulaFingerprint | None

    # Character balance
    character_vector: dict[str, float] | None
    character_coverage_fraction: float
    character_missing_materials: list[str]
    weight_diagnosis: WeightDiagnosis | None

    # Structural analysis
    role_coverage: dict[str, int]    # role → count of materials filling it
    note_coverage: dict[str, int]    # top/heart/base → count
    texture_coverage: dict[str, int] # texture → count
    structural_gaps: list[StructuralGap]

    # Synergy
    synergy_report: SynergyReport

    # Musk compatibility
    musk_analysis: MuskCompatibility

    # Temporal
    temporal: TemporalProfile

    # Overall health score
    health_score: float | None  # 0-100, unavailable for incomplete character evidence

    def summary_lines(self) -> list[str]:
        """Generate human-readable summary lines."""
        lines = [
            f"═══ Chemical Life Graph: {self.formula_name} ═══",
            f"Materials: {self.ingredient_count} | Mass: {self.total_mass_ul:.0f} µL | Concentrate: {self.concentrate_pct:.1f}% | Mode: {self.structure_mode}",
            "",
            (
                f"Health Score: {self.health_score:.0f}/100"
                if self.health_score is not None
                else "Health Score: UNKNOWN (incomplete numeric character evidence)"
            ),
            "",
        ]

        # Character balance
        lines.append("── Character Balance ──")
        if self.character_vector is None or self.weight_diagnosis is None:
            lines.append(
                "  Unavailable; missing numeric character evidence for: "
                + ", ".join(self.character_missing_materials)
            )
        else:
            top3 = sorted(
                self.character_vector.items(), key=lambda x: x[1], reverse=True
            )[:3]
            lines.append(f"  Dominant: {', '.join(f'{d}={v:.1f}' for d, v in top3)}")
            if self.weight_diagnosis.overweight:
                ow = ", ".join(
                    f"{d} (+{v:.1f})" for d, v in self.weight_diagnosis.overweight[:3]
                )
                lines.append(f"  Overweight: {ow}")
            if self.weight_diagnosis.underweight:
                uw = ", ".join(
                    f"{d} (−{v:.1f})" for d, v in self.weight_diagnosis.underweight[:3]
                )
                lines.append(f"  Underweight: {uw}")
            lines.append(f"  Balance Score: {self.weight_diagnosis.balance_score:.0f}/100")
        lines.append("")

        # Role coverage
        lines.append("── Role Coverage ──")
        for role, count in sorted(self.role_coverage.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"  {role}: {count} material(s)")
        lines.append("")

        # Gaps
        if self.structural_gaps:
            lines.append("── Structural Gaps ──")
            for gap in self.structural_gaps[:5]:
                lines.append(f"  [{gap.severity:.0%}] Missing {gap.gap_type}: {gap.name}")
                lines.append(f"         → {gap.suggestion}")
                if gap.candidates:
                    lines.append(f"         Candidates: {', '.join(gap.candidates[:4])}")
            lines.append("")

        # Synergy
        lines.append("── Synergy Report ──")
        lines.append(f"  Overall synergy: {self.synergy_report.overall_synergy:+.3f}")
        if self.synergy_report.strongest_pairs:
            best = self.synergy_report.strongest_pairs[0]
            lines.append(f"  Best pair: {best[0]} + {best[1]} ({best[2]:+.3f})")
        if self.synergy_report.clash_pairs:
            worst = self.synergy_report.clash_pairs[0]
            lines.append(f"  Clash: {worst[0]} + {worst[1]} ({worst[2]:+.3f})")
        if self.synergy_report.stacks:
            lines.append(f"  Synergy stacks found: {len(self.synergy_report.stacks)}")
            for stack in self.synergy_report.stacks[:3]:
                lines.append(f"    • {' + '.join(stack.materials)} (avg={stack.avg_synergy:.3f})")
        lines.append("")

        # Musk compatibility
        lines.append("── Musk Compatibility ──")
        if self.musk_analysis.already_present:
            lines.append(f"  Present: {', '.join(self.musk_analysis.already_present)}")
        if self.musk_analysis.recommended:
            for musk, score, reason in self.musk_analysis.recommended[:3]:
                lines.append(f"  ✓ Recommended: {musk} ({score:+.3f}) — {reason}")
        if self.musk_analysis.too_heavy:
            for musk, score, reason in self.musk_analysis.too_heavy[:2]:
                lines.append(f"  ✗ Too heavy: {musk} ({score:+.3f}) — {reason}")
        lines.append("")

        # Temporal
        lines.append("── Temporal Evolution ──")
        lines.append(
            "  Top-dominance model window: "
            f"~{self.temporal.top_dominance_model_minutes:.0f} model-min"
        )
        if self.temporal.base_dominance_model_hours is None:
            lines.append("  Base-dominance model window: not reached")
        else:
            lines.append(
                "  Base-dominance model window: "
                f"~{self.temporal.base_dominance_model_hours:.0f} model-hr"
            )
        lines.append(
            "  Absolute longevity: unavailable; calibrated skin or blotter "
            "measurements required"
        )
        lines.append(f"  Temporal authority: {self.temporal.authority}")
        lines.append(f"  Linearity: {self.temporal.linear_score:.0%}")

        return lines


# ═══════════════════════════════════════════════════════════════════════════════
# Balance Targets — what a "balanced" formula looks like per style
# ═══════════════════════════════════════════════════════════════════════════════

_STYLE_TARGETS: dict[str, dict[str, float]] = {
    "classical": {
        "warmth": 4, "sweetness": 3, "freshness": 4, "powdery": 3,
        "green": 3, "animalic": 2, "radiance": 5, "woody": 4,
        "spicy": 2, "floral": 5, "smoky": 1, "creamy": 3,
    },
    "fresh": {
        "warmth": 2, "sweetness": 2, "freshness": 7, "powdery": 2,
        "green": 5, "animalic": 1, "radiance": 6, "woody": 3,
        "spicy": 2, "floral": 3, "smoky": 0, "creamy": 2,
    },
    "oriental": {
        "warmth": 7, "sweetness": 6, "freshness": 2, "powdery": 4,
        "green": 1, "animalic": 4, "radiance": 3, "woody": 4,
        "spicy": 5, "floral": 3, "smoky": 3, "creamy": 5,
    },
    "woody": {
        "warmth": 4, "sweetness": 2, "freshness": 3, "powdery": 3,
        "green": 2, "animalic": 2, "radiance": 3, "woody": 7,
        "spicy": 2, "floral": 2, "smoky": 2, "creamy": 3,
    },
    "chypre": {
        "warmth": 3, "sweetness": 2, "freshness": 4, "powdery": 3,
        "green": 4, "animalic": 3, "radiance": 4, "woody": 5,
        "spicy": 2, "floral": 4, "smoky": 2, "creamy": 2,
    },
    "skin_scent": {
        "warmth": 4, "sweetness": 3, "freshness": 3, "powdery": 5,
        "green": 2, "animalic": 2, "radiance": 6, "woody": 4,
        "spicy": 1, "floral": 3, "smoky": 1, "creamy": 5,
    },
}

# Required roles for a structurally complete formula
_REQUIRED_ROLES = {
    "formula": ["character", "fixative", "volume", "radiance"],
    "module": ["character"],
}
_IMPORTANT_ROLES = ["modifier", "bridge", "trace"]

# Required note coverage
_REQUIRED_NOTES = {
    "formula": {"top": 1, "heart": 2, "base": 2},
    "module": {"heart": 1},
}


# ═══════════════════════════════════════════════════════════════════════════════
# Chemical Life Graph Builder
# ═══════════════════════════════════════════════════════════════════════════════

def build_chemical_life_graph(
    formula_name: str,
    ingredients: dict[str, float],
    ethanol_ml: float = 0.0,
    style: str = "classical",
    structure_mode: str = "formula",
    synergy_graph: SynergyGraph | None = None,
) -> ChemicalLifeGraph:
    """Build a complete chemical life graph for a formula.

    Args:
        formula_name: Human-readable name for the formula.
        ingredients: {material_name: amount_in_µL} mapping (concentrate only).
        ethanol_ml: Amount of ethanol in mL.
        style: Formula style for balance targets ("classical", "fresh", "oriental",
               "woody", "chypre", "skin_scent").
        synergy_graph: Pre-built SynergyGraph, or None to build one on the fly.
        structure_mode: "formula" for finished perfumes, "module" for accords/boosters.

    Returns:
        ChemicalLifeGraph with full diagnostic.
    """
    total_mass_ul = sum(ingredients.values())
    total_ml = total_mass_ul / 1000.0 + ethanol_ml
    concentrate_pct = (total_mass_ul / 1000.0) / total_ml * 100 if total_ml > 0 else 0

    # ── 1. Character vector (mass-weighted) ──
    fp = fingerprint_formula(formula_name, ingredients)
    character = _compute_character(ingredients)

    # ── 2. Weight diagnosis ──
    target = _STYLE_TARGETS.get(style, _STYLE_TARGETS["classical"])
    weight_diag = _diagnose_weight(character, target) if character is not None else None

    # ── 3. Role, note, texture coverage ──
    role_cov, note_cov, texture_cov = _coverage_analysis(ingredients)

    # ── 4. Structural gaps ──
    gaps = _detect_gaps(
        role_cov,
        note_cov,
        texture_cov,
        character,
        target,
        ingredients,
        structure_mode=structure_mode,
    )

    # ── 5. Synergy analysis ──
    if synergy_graph is None:
        synergy_graph = SynergyGraph()
        synergy_graph.build(list(ingredients.keys()))
    synergy_report = _synergy_analysis(ingredients, synergy_graph)

    # ── 7. Musk compatibility ──
    musk_analysis = synergy_graph.analyze_musk_compatibility(ingredients)

    # ── 8. Temporal evolution ──
    temporal = _temporal_analysis(ingredients)

    # ── 9. Overall health score ──
    health = (
        _compute_health(
            weight_diag, role_cov, note_cov, gaps,
            synergy_report, temporal, concentrate_pct,
            structure_mode=structure_mode,
        )
        if weight_diag is not None
        else None
    )

    return ChemicalLifeGraph(
        formula_name=formula_name,
        structure_mode=structure_mode,
        ingredient_count=len(ingredients),
        total_mass_ul=total_mass_ul,
        concentrate_pct=concentrate_pct,
        fingerprint=fp,
        character_vector=character,
        character_coverage_fraction=fp.character_coverage_fraction,
        character_missing_materials=fp.character_missing_materials,
        weight_diagnosis=weight_diag,
        role_coverage=role_cov,
        note_coverage=note_cov,
        texture_coverage=texture_cov,
        structural_gaps=gaps,
        synergy_report=synergy_report,
        musk_analysis=musk_analysis,
        temporal=temporal,
        health_score=health,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Internal Analysis Functions
# ═══════════════════════════════════════════════════════════════════════════════

def _compute_character(ingredients: dict[str, float]) -> dict[str, float] | None:
    """Mass-weighted character vector for the formula."""
    totals = {d: 0.0 for d in DIMENSIONS}
    total_mass = sum(ingredients.values())
    if total_mass <= 0:
        return totals

    for name, amount in ingredients.items():
        profile = get_profile(name)
        if not profile or profile.numeric_character is None:
            return None
        w = amount / total_mass
        for dim in DIMENSIONS:
            totals[dim] += profile.numeric_character.get(dim, 0) * w

    return {d: round(v, 2) for d, v in totals.items()}


def _diagnose_weight(
    character: dict[str, float],
    target: dict[str, float],
) -> WeightDiagnosis:
    """Compare formula character against style target, find over/under."""
    overweight = []
    underweight = []
    total_deviation = 0.0

    for dim in DIMENSIONS:
        actual = character.get(dim, 0)
        tgt = target.get(dim, 3.0)
        diff = actual - tgt
        total_deviation += abs(diff)

        if diff > 1.5:
            overweight.append((dim, round(diff, 2)))
        elif diff < -1.5:
            underweight.append((dim, round(abs(diff), 2)))

    overweight.sort(key=lambda x: x[1], reverse=True)
    underweight.sort(key=lambda x: x[1], reverse=True)

    # Balance score: 100 when perfect, decreases with deviation
    max_possible_dev = len(DIMENSIONS) * 10.0
    balance = max(0, 100 * (1 - total_deviation / max_possible_dev))

    return WeightDiagnosis(
        overweight=overweight,
        underweight=underweight,
        balance_score=round(balance, 1),
    )


def _coverage_analysis(
    ingredients: dict[str, float],
) -> tuple[dict[str, int], dict[str, int], dict[str, int]]:
    """Count role, note, and texture coverage."""
    roles: dict[str, int] = {}
    notes: dict[str, int] = {"top": 0, "heart": 0, "base": 0}
    textures: dict[str, int] = {}

    for name in ingredients:
        profile = get_profile(name)
        if not profile:
            continue

        # Role
        role = profile.role
        roles[role] = roles.get(role, 0) + 1

        # Note
        note = profile.note
        if note in notes:
            notes[note] += 1

        # Texture
        if profile.texture:
            textures[profile.texture] = textures.get(profile.texture, 0) + 1

    return roles, notes, textures


def _detect_gaps(
    role_cov: dict[str, int],
    note_cov: dict[str, int],
    texture_cov: dict[str, int],
    character: dict[str, float] | None,
    target: dict[str, float],
    ingredients: dict[str, float],
    structure_mode: str = "formula",
) -> list[StructuralGap]:
    """Identify structural gaps in the formula."""
    gaps = []
    all_profiles = get_all_profiles()
    ingredient_set = set(ingredients.keys())
    required_roles = _REQUIRED_ROLES.get(structure_mode, _REQUIRED_ROLES["formula"])
    required_notes = _REQUIRED_NOTES.get(structure_mode, _REQUIRED_NOTES["formula"])

    # Missing required roles
    for role in required_roles:
        if role_cov.get(role, 0) == 0:
            candidates = [
                name for name, p in all_profiles.items()
                if p and p.role == role and name not in ingredient_set
            ]
            gaps.append(StructuralGap(
                gap_type="role",
                name=role,
                severity=0.9,
                suggestion=f"Add a {role} material for structural completeness",
                candidates=candidates[:5],
            ))
        elif role_cov.get(role, 0) == 1 and role in ("character", "fixative"):
            candidates = [
                name for name, p in all_profiles.items()
                if p and p.role == role and name not in ingredient_set
            ]
            gaps.append(StructuralGap(
                gap_type="role",
                name=f"second {role}",
                severity=0.4,
                suggestion=f"Consider a second {role} for depth",
                candidates=candidates[:5],
            ))

    # Missing important roles (lower severity)
    for role in _IMPORTANT_ROLES:
        if role_cov.get(role, 0) == 0:
            candidates = [
                name for name, p in all_profiles.items()
                if p and p.role == role and name not in ingredient_set
            ]
            if candidates:
                gaps.append(StructuralGap(
                    gap_type="role",
                    name=role,
                    severity=0.5,
                    suggestion=f"A {role} material would add nuance",
                    candidates=candidates[:5],
                ))

    # Note balance gaps
    for note, min_count in required_notes.items():
        actual = note_cov.get(note, 0)
        if actual < min_count:
            candidates = [
                name for name, p in all_profiles.items()
                if p and p.note == note and name not in ingredient_set
            ]
            gaps.append(StructuralGap(
                gap_type="note",
                name=f"{note} notes ({actual}/{min_count})",
                severity=0.7 if actual == 0 else 0.4,
                suggestion=f"Add {min_count - actual} more {note} note material(s)",
                candidates=candidates[:5],
            ))

    # Texture diversity gap — formula should have at least 2 different textures
    if len(texture_cov) < 2:
        missing_textures = {"cushion", "cocoon", "halo", "veil", "skin-effect"} - set(texture_cov.keys())
        candidates = []
        for tex in missing_textures:
            for name, p in all_profiles.items():
                if p and p.texture == tex and name not in ingredient_set:
                    candidates.append(name)
                    break
        gaps.append(StructuralGap(
            gap_type="texture",
            name="texture diversity",
            severity=0.5,
            suggestion="Add materials with different textures for dimension",
            candidates=candidates[:5],
        ))

    # Character dimension gaps — underweight dimensions that matter for the style
    for dim in DIMENSIONS if character is not None else ():
        actual = character.get(dim, 0)
        tgt = target.get(dim, 3.0)
        if tgt >= 4.0 and actual < tgt - 2.0:
            # This dimension matters for the style but is significantly low
            candidates = [
                name for name, p in all_profiles.items()
                if (
                    p
                    and p.numeric_character is not None
                    and p.numeric_character.get(dim, 0) >= 6.0
                    and name not in ingredient_set
                )
            ]
            gaps.append(StructuralGap(
                gap_type="dimension",
                name=f"{dim} (need {tgt:.0f}, have {actual:.1f})",
                severity=min(0.8, (tgt - actual) / 10.0),
                suggestion=f"Add materials with high {dim} character",
                candidates=candidates[:5],
            ))

    gaps.sort(key=lambda g: g.severity, reverse=True)
    return gaps


def _synergy_analysis(
    ingredients: dict[str, float],
    graph: SynergyGraph,
) -> SynergyReport:
    """Analyze synergies within the formula."""
    names = list(ingredients.keys())
    overall = graph.formula_synergy_score(names)

    # All pairwise scores
    pairs = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            score = graph.pair_synergy(a, b)
            pairs.append((a, b, score))

    pairs.sort(key=lambda x: x[2], reverse=True)
    strongest = [(a, b, round(s, 3)) for a, b, s in pairs if s > 0][:5]
    weakest = [(a, b, round(s, 3)) for a, b, s in pairs if s == 0][:5]
    clashes = [(a, b, round(s, 3)) for a, b, s in pairs if s < 0]

    stacks = graph.find_synergy_stacks(names)

    return SynergyReport(
        overall_synergy=round(overall, 3),
        strongest_pairs=strongest,
        weakest_pairs=weakest,
        clash_pairs=clashes,
        stacks=stacks,
    )


def _temporal_analysis(ingredients: dict[str, float]) -> TemporalProfile:
    """Run volatility simulation and extract temporal metrics."""
    sim = VolatilityCurveSimulator()
    # Convert µL amounts to percentages for the simulator
    total = sum(ingredients.values())
    if total <= 0:
        return TemporalProfile(
            note_transitions=[],
            longevity_hours=None,
            top_dominance_model_minutes=0,
            base_dominance_model_hours=None,
            linear_score=0,
            authority="HEURISTIC_UNCALIBRATED",
            release_authority=False,
        )

    pct_ingredients = {name: (amt / total) * 100 for name, amt in ingredients.items()}
    profile = sim.simulate(pct_ingredients)

    # Extract transitions
    transitions = []
    for i in range(1, len(profile.dominant_notes)):
        if profile.dominant_notes[i] != profile.dominant_notes[i - 1]:
            transitions.append({
                "time": profile.time_labels[i],
                "hours": profile.time_points[i],
                "from": profile.dominant_notes[i - 1],
                "to": profile.dominant_notes[i],
            })

    # Top dominance duration (minutes)
    top_dom_model_min = 0.0
    for i, note in enumerate(profile.dominant_notes):
        if note == "top":
            if i + 1 < len(profile.time_points):
                top_dom_model_min = profile.time_points[i + 1] * 60
            else:
                top_dom_model_min = profile.time_points[i] * 60
        else:
            break

    # First heuristic frame where base-note share exceeds 80%. This is a
    # compositional model window, not measured persistence or longevity.
    base_dom_model_hours: float | None = None
    for i, evolution in enumerate(profile.note_evolution):
        base_share = evolution.get("base", 0)
        if base_share > 80 and i > 0:
            base_dom_model_hours = profile.time_points[i]
            break

    # Linearity score — how much the note evolution changes over time
    changes = 0
    for i in range(1, len(profile.note_evolution)):
        prev = profile.note_evolution[i - 1]
        curr = profile.note_evolution[i]
        for key in ("top", "heart", "base"):
            changes += abs(curr.get(key, 0) - prev.get(key, 0))
    max_change = len(profile.note_evolution) * 300  # theoretical max
    linearity = 1.0 - (changes / max_change) if max_change > 0 else 0.5

    return TemporalProfile(
        note_transitions=transitions,
        longevity_hours=None,
        top_dominance_model_minutes=top_dom_model_min,
        base_dominance_model_hours=base_dom_model_hours,
        linear_score=round(max(0, min(1, linearity)), 2),
        authority="HEURISTIC_UNCALIBRATED",
        release_authority=False,
    )


def _compute_health(
    weight_diag: WeightDiagnosis,
    role_cov: dict[str, int],
    note_cov: dict[str, int],
    gaps: list[StructuralGap],
    synergy: SynergyReport,
    temporal: TemporalProfile,
    concentrate_pct: float,
    structure_mode: str = "formula",
) -> float:
    """Compute overall formula health score 0-100."""
    score = 100.0
    required_roles = _REQUIRED_ROLES.get(structure_mode, _REQUIRED_ROLES["formula"])
    required_notes = _REQUIRED_NOTES.get(structure_mode, _REQUIRED_NOTES["formula"])

    # Balance penalty (up to -25)
    score -= max(0, 25 - weight_diag.balance_score * 0.25)

    # Structural gap penalty
    gap_multiplier = 2.5 if structure_mode == "module" else 5.0
    gap_cap = 15 if structure_mode == "module" else 30
    gap_penalty = sum(g.severity for g in gaps) * gap_multiplier
    score -= min(gap_cap, gap_penalty)

    # Role coverage bonus/penalty
    required_filled = sum(1 for r in required_roles if role_cov.get(r, 0) > 0)
    score += (required_filled / max(1, len(required_roles))) * 10 - 5

    # Note coverage
    notes_ok = all(note_cov.get(n, 0) >= c for n, c in required_notes.items())
    if not notes_ok:
        score -= 4 if structure_mode == "module" else 10

    # Synergy bonus (up to +10)
    score += max(-5, min(10, synergy.overall_synergy * 20))

    # Clash penalty
    score -= len(synergy.clash_pairs) * 3

    # Concentration range check (should be 10-30% typically)
    if structure_mode != "module" and concentrate_pct < 5:
        score -= 10
    elif structure_mode != "module" and concentrate_pct > 40:
        score -= 5

    # The temporal simulator has no skin/blotter calibration. Its model-window
    # timing therefore remains diagnostic and must not alter formula health.

    return round(max(0, min(100, score)), 1)


# ═══════════════════════════════════════════════════════════════════════════════
# Batch Analysis — run on all formulas
# ═══════════════════════════════════════════════════════════════════════════════

def batch_analyze(
    formulas: dict[str, dict[str, float]],
    style: str = "classical",
) -> dict[str, ChemicalLifeGraph]:
    """Build chemical life graphs for multiple formulas.

    Args:
        formulas: {formula_name: {material_name: amount_µL}} mapping.
        style: Style target for weight diagnosis.

    Returns:
        {formula_name: ChemicalLifeGraph} mapping.
    """
    # Build one shared synergy graph for efficiency
    all_materials = set()
    for ingredients in formulas.values():
        all_materials.update(ingredients.keys())

    graph = SynergyGraph()
    graph.build(list(all_materials))

    results = {}
    for name, ingredients in formulas.items():
        results[name] = build_chemical_life_graph(
            formula_name=name,
            ingredients=ingredients,
            style=style,
            synergy_graph=graph,
        )

    return results


def print_life_graph(graph: ChemicalLifeGraph) -> None:
    """Print a chemical life graph to stdout."""
    for line in graph.summary_lines():
        print(line)
