"""Reconstruction Pipeline — Multi-module orchestrator with category-based scoring.

This is the master module that runs ALL evidence-analysis modules when
reconstructing a fragrance, then produces a scored report broken down by
CATEGORY (not a single geometric mean).

Category-based scoring philosophy (user requirement):
  "not by geometric mean concept, but by the category of score,
   in order for the user to know what is good and what is not
   by different metrics"

Each module produces its own 0–100 score in a specific category:

  ┌─────────────────────────────┬─────────────────────────────────────────┐
  │ Category                    │ Module                                  │
  ├─────────────────────────────┼─────────────────────────────────────────┤
  │ BAYESIAN_POSTERIOR          │ reverse_engineer.py                     │
  │ ALLERGEN_EVIDENCE           │ ifra_constraints.py                     │
  │ ALLERGEN_CHEMISTRY          │ allergen_solver.py                      │
  │ PERFUMER_ATTRIBUTION        │ perfumer_signature.py                   │
  │ ECONOMIC_PLAUSIBILITY       │ cost_analysis.py                        │
  │ PERCEPTUAL_CONSISTENCY      │ odor_thresholds.py                      │
  │ MATERIAL_INTERACTIONS       │ material_interactions.py                │
  └─────────────────────────────┴─────────────────────────────────────────┘

Usage:
    spec = FragranceSpec(
        name="Amouage Opus V",
        perfumer="Dominique Ropion",
        house="Amouage",
        year=2018,
        retail_price_usd=230.0,
        concentration_pct=25.0,
        ...
    )
    report = run_reconstruction_pipeline(spec)
    print(format_pipeline_report(report))
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from engine.allergen_solver import (
    AllergenSolverResult,
    solve_allergen_ratios,
)
from engine.captive_availability import (
    CaptiveAnalysisResult,
    analyze_captive_availability,
)
from engine.cost_analysis import (
    COGAnalysisResult,
    analyze_cost_of_goods,
)
from engine.ifra_constraints import (
    IFRAAnalysisResult,
    compute_ifra_windows,
)
from engine.material_interactions import (
    InteractionAnalysisResult,
    analyze_material_interactions,
)
from engine.molecular_weight_distribution import (
    MWAnalysisResult,
    analyze_mw_distribution,
)
from engine.odor_thresholds import (
    ODTAnalysisResult,
    analyze_odor_thresholds,
)
from engine.perfumer_signature import (
    SignatureAnalysisResult,
    analyze_perfumer_signature,
)
from engine.regulatory_timeline import (
    RegulatoryAnalysisResult,
    analyze_regulatory_timeline,
)

# ── Internal module imports ────────────────────────────────────────
from engine.reverse_engineer import (
    EvidenceItem,
    EvidencePool,
    ReconstructedFormula,
    format_reconstruction_report,
    parse_allergen_list,
    parse_note_pyramid,
    parse_review_consensus,
    reverse_engineer,
)
from engine.temporal_volatility import (
    TemporalAnalysisResult,
    analyze_temporal_consistency,
)

# ── Tracing ───────────────────────────────────────────────────────
from engine.tracing import traced
from engine.vapor_pressure_modeling import (
    VPAnalysisResult,
    analyze_vapor_pressure,
)

# ══════════════════════════════════════════════════════════════════════
# Input specification
# ══════════════════════════════════════════════════════════════════════

@dataclass
class FragranceSpec:
    """Everything known about a target fragrance, fed to the pipeline."""
    name: str
    perfumer: str = ""
    house: str = ""
    year: int = 0
    retail_price_usd: float = 0.0
    bottle_size_ml: float = 100.0
    concentration_pct: float = 25.0          # EDP default

    # Note pyramid (marketing / official)
    top_notes: list[str] = field(default_factory=list)
    heart_notes: list[str] = field(default_factory=list)
    base_notes: list[str] = field(default_factory=list)

    # Allergen declaration (ordered list from box)
    declared_allergens: list[str] = field(default_factory=list)

    # Community review data: note → fraction of reviewers detecting
    community_votes: dict[str, float] = field(default_factory=dict)
    total_reviewers: int = 200

    # Expert / blog evidence
    expert_claims: list[dict] = field(default_factory=list)
    # Format: [{"material": "Iso E Super", "confidence": 0.7, "text": "...", "source": "url"}]

    # GC-MS evidence if available
    gcms_peaks: list[dict] = field(default_factory=list)
    # Format: [{"material": "AIMI", "pct": 17.8, "confidence": 0.95}]

    # Patent evidence
    patent_formulas: list[dict] = field(default_factory=list)
    # Format: [{"patent_id": "US...", "materials": {"Hedione": 18.5, ...}}]

    # Known allergen ratios (from GC-MS of naturals)
    allergen_ratios: dict[str, float] = field(default_factory=dict)
    # e.g. {"citronellol:geraniol": 1.94}

    # Additional evidence items (pre-built)
    additional_evidence: list[EvidenceItem] = field(default_factory=list)

    # Price tier override
    price_tier: str = ""  # "mass_market", "premium_designer", "luxury_niche", "ultra_luxury"

    # Materials % estimate for COG (sum of raw materials as % of concentrate cost)
    estimated_materials_pct: dict[str, float] = field(default_factory=dict)

    # Fragrance family for MW distribution analysis
    fragrance_family: str = ""  # e.g. "iris", "oriental", "woody", "chypre"

    # Known fragrance reformulation year (for regulatory checks)
    known_reformulation_year: Optional[int] = None


# ══════════════════════════════════════════════════════════════════════
# Category scoring definitions
# ══════════════════════════════════════════════════════════════════════

SCORE_CATEGORIES = [
    "BAYESIAN_POSTERIOR",
    "ALLERGEN_EVIDENCE",
    "ALLERGEN_CHEMISTRY",
    "PERFUMER_ATTRIBUTION",
    "ECONOMIC_PLAUSIBILITY",
    "PERCEPTUAL_CONSISTENCY",
    "MATERIAL_INTERACTIONS",
    "SILLAGE_PREDICTION",
    "TEMPORAL_CONSISTENCY",
    "SUPPLY_CHAIN_PLAUSIBILITY",
    "REGULATORY_CONSISTENCY",
    "PHYSICOCHEMICAL_COHERENCE",
]

# Score quality labels (what each range MEANS to the user)
SCORE_LABELS = {
    (90, 100): "Excellent — near-certain intelligence",
    (75, 89):  "Strong — high-confidence constraints",
    (60, 74):  "Good — meaningful but incomplete",
    (40, 59):  "Moderate — partial signal, gaps remain",
    (20, 39):  "Weak — limited data, speculative",
    (0, 19):   "Minimal — insufficient evidence",
}


def _label_score(score: float) -> str:
    """Return human-readable label for a score."""
    for (lo, hi), label in SCORE_LABELS.items():
        if lo <= score <= hi:
            return label
    return "Unknown"


@dataclass
class CategoryScore:
    """One category's score with context."""
    category: str
    score: float             # 0–100
    label: str               # Human-readable quality label
    detail: str              # Brief explanation for user
    actionable_insights: list[str] = field(default_factory=list)


@dataclass
class PipelineReport:
    """Complete reconstruction output with category-based scores."""
    target_name: str
    timestamp: str
    elapsed_seconds: float

    # Per-module results
    bayesian_result: Optional[ReconstructedFormula] = None
    ifra_result: Optional[IFRAAnalysisResult] = None
    allergen_result: Optional[AllergenSolverResult] = None
    perfumer_result: Optional[SignatureAnalysisResult] = None
    cost_result: Optional[COGAnalysisResult] = None
    odt_result: Optional[ODTAnalysisResult] = None
    interaction_result: Optional[InteractionAnalysisResult] = None
    vp_result: Optional[VPAnalysisResult] = None
    temporal_result: Optional[TemporalAnalysisResult] = None
    captive_result: Optional[CaptiveAnalysisResult] = None
    regulatory_result: Optional[RegulatoryAnalysisResult] = None
    mw_result: Optional[MWAnalysisResult] = None

    # Category scores (the key output)
    category_scores: list[CategoryScore] = field(default_factory=list)

    # Aggregated material list with all adjustments applied
    final_materials: dict[str, dict] = field(default_factory=dict)
    # material → {posterior, tier, concentration_pct, sources, interactions, ...}

    # Optimization recommendations per category
    optimization_targets: list[str] = field(default_factory=list)

    @property
    def weakest_category(self) -> Optional[CategoryScore]:
        """The weakest scoring category — primary optimization target."""
        if not self.category_scores:
            return None
        return min(self.category_scores, key=lambda c: c.score)

    @property
    def strongest_category(self) -> Optional[CategoryScore]:
        if not self.category_scores:
            return None
        return max(self.category_scores, key=lambda c: c.score)

    @property
    def overall_confidence(self) -> float:
        """Weighted average across categories (NOT geometric mean — user requirement)."""
        if not self.category_scores:
            return 0.0
        # Arithmetic mean — transparent and interpretable
        return sum(c.score for c in self.category_scores) / len(self.category_scores)


# ══════════════════════════════════════════════════════════════════════
# Pipeline execution
# ══════════════════════════════════════════════════════════════════════

@traced("pipeline.run")
def run_reconstruction_pipeline(spec: FragranceSpec) -> PipelineReport:
    """Execute the full multi-module reconstruction pipeline.

    Runs each module independently, collects per-category scores,
    then merges material lists with interaction adjustments.
    """
    start = time.time()
    report = PipelineReport(
        target_name=spec.name,
        timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
        elapsed_seconds=0.0,
    )

    # ── Stage 1: Build evidence pool and run Bayesian engine ──────
    pool = EvidencePool(spec.name)

    # Add allergen evidence
    if spec.declared_allergens:
        allergen_items = parse_allergen_list(", ".join(spec.declared_allergens))
        pool.add_many(allergen_items)

    # Add note pyramid evidence
    if spec.top_notes or spec.heart_notes or spec.base_notes:
        pyramid_items = parse_note_pyramid(
            top=spec.top_notes,
            heart=spec.heart_notes,
            base=spec.base_notes,
        )
        pool.add_many(pyramid_items)

    # Add community review evidence
    if spec.community_votes:
        review_items = parse_review_consensus(
            spec.community_votes, spec.total_reviewers
        )
        pool.add_many(review_items)

    # Add expert evidence
    for expert in spec.expert_claims:
        pool.add(EvidenceItem(
            source_type="expert",
            material=expert.get("material", ""),
            confidence=expert.get("confidence", 0.6),
            concentration_pct=expert.get("concentration_pct"),
            raw_text=expert.get("text", ""),
            source_url=expert.get("source", ""),
        ))

    # Add GC-MS evidence
    for peak in spec.gcms_peaks:
        pool.add(EvidenceItem(
            source_type="gcms",
            material=peak.get("material", ""),
            confidence=peak.get("confidence", 0.9),
            concentration_pct=peak.get("pct"),
            raw_text=f"GC-MS peak: {peak.get('material', '')} at {peak.get('pct', '?')}%",
        ))

    # Add patent evidence
    for patent in spec.patent_formulas:
        patent_id = patent.get("patent_id", "")
        for mat, pct in patent.get("materials", {}).items():
            pool.add(EvidenceItem(
                source_type="patent",
                material=mat,
                confidence=0.55,
                concentration_pct=pct,
                raw_text=f"Patent {patent_id}: {mat} at {pct:.1f}%",
            ))

    # Add any additional pre-built evidence
    pool.add_many(spec.additional_evidence)

    # Run Bayesian engine
    bayesian = reverse_engineer(pool)
    report.bayesian_result = bayesian

    # Compute Bayesian category score
    n_confirmed = 0
    n_probable = 0
    n_total = 0
    if bayesian.materials:
        n_confirmed = len(bayesian.confirmed)
        n_probable = len(bayesian.probable)
        n_total = len(bayesian.materials)
        avg_posterior = sum(m.posterior for m in bayesian.materials) / n_total
        bayesian_score = min(100.0,
            n_confirmed * 4.0 + n_probable * 2.0 + avg_posterior * 40.0
        )
    else:
        bayesian_score = 0.0

    bayesian_insights = []
    if bayesian.conflict_flags:
        bayesian_insights.append(f"{len(bayesian.conflict_flags)} conflicts detected — review evidence chains")
    if not bayesian.actionable:
        bayesian_insights.append("Not yet actionable — need more CONFIRMED materials (≥80% mass)")
    if n_confirmed < 5:
        bayesian_insights.append(f"Only {n_confirmed} confirmed materials — add GC-MS or allergen data")

    report.category_scores.append(CategoryScore(
        category="BAYESIAN_POSTERIOR",
        score=bayesian_score,
        label=_label_score(bayesian_score),
        detail=f"{n_confirmed} confirmed, {n_probable} probable of {n_total} total materials",
        actionable_insights=bayesian_insights,
    ))

    # ── Stage 2: IFRA Constraint Analysis ─────────────────────────
    if spec.declared_allergens:
        ifra = compute_ifra_windows(
            declared_allergens=spec.declared_allergens,
            concentration_pct=spec.concentration_pct,
            target_name=spec.name,
        )
        report.ifra_result = ifra

        ifra_insights = []
        if ifra.restricted_materials:
            ifra_insights.append(f"IFRA-restricted: {', '.join(ifra.restricted_materials)}")
        if ifra.absent_allergens:
            ifra_insights.append(f"{len(ifra.absent_allergens)} allergens absent — eliminates materials")

        report.category_scores.append(CategoryScore(
            category="ALLERGEN_EVIDENCE",
            score=ifra.score,
            label=_label_score(ifra.score),
            detail=f"{ifra.total_constrained} declared allergens, {len(ifra.restricted_materials)} IFRA-restricted",
            actionable_insights=ifra_insights,
        ))
    else:
        report.category_scores.append(CategoryScore(
            category="ALLERGEN_EVIDENCE",
            score=0.0,
            label=_label_score(0.0),
            detail="No allergen data provided — obtain box allergen list",
            actionable_insights=["Photograph the fragrance box allergen declaration"],
        ))

    # ── Stage 3: Allergen Ratio Solver ────────────────────────────
    if spec.declared_allergens:
        allergen_sol = solve_allergen_ratios(
            target_name=spec.name,
            declared_allergens=spec.declared_allergens,
            concentrate_pct=spec.concentration_pct,
            known_ratios=spec.allergen_ratios if spec.allergen_ratios else None,
        )
        report.allergen_result = allergen_sol

        chem_insights = []
        for solved in allergen_sol.solved_naturals:
            chem_insights.append(
                f"{solved.material}: {solved.best_estimate_pct:.2f}% "
                f"({solved.method}, conf={solved.confidence:.2f})"
            )
        if allergen_sol.deficit_analysis:
            for allergen, deficit in allergen_sol.deficit_analysis.items():
                chem_insights.append(f"Deficit in {allergen}: {deficit:.3f}% — implies synthetic addition")

        report.category_scores.append(CategoryScore(
            category="ALLERGEN_CHEMISTRY",
            score=allergen_sol.score,
            label=_label_score(allergen_sol.score),
            detail=f"{len(allergen_sol.solved_naturals)} naturals back-calculated from {len(allergen_sol.equations)} allergen equations",
            actionable_insights=chem_insights,
        ))
    else:
        report.category_scores.append(CategoryScore(
            category="ALLERGEN_CHEMISTRY",
            score=0.0,
            label=_label_score(0.0),
            detail="No allergen chemistry data — need declared allergens + known ratios",
        ))

    # ── Stage 4: Perfumer Signature Analysis ──────────────────────
    if spec.perfumer or spec.house:
        perfumer_res = analyze_perfumer_signature(
            perfumer=spec.perfumer,
            house=spec.house,
            year=spec.year,
            materials_to_check=[m.name for m in bayesian.materials] if bayesian.materials else [],
        )
        report.perfumer_result = perfumer_res

        sig_insights = []
        if perfumer_res.perfumer_found:
            top_priors = sorted(perfumer_res.priors, key=lambda p: p.combined_prior, reverse=True)[:5]
            for p in top_priors:
                sig_insights.append(f"{p.material}: portfolio freq={p.combined_prior:.2f}")
        else:
            sig_insights.append(f"Perfumer '{spec.perfumer}' not in database — no portfolio priors")

        report.category_scores.append(CategoryScore(
            category="PERFUMER_ATTRIBUTION",
            score=perfumer_res.score,
            label=_label_score(perfumer_res.score),
            detail=f"Perfumer: {'FOUND' if perfumer_res.perfumer_found else 'NOT FOUND'}, "
                   f"House: {'FOUND' if perfumer_res.house_found else 'NOT FOUND'}",
            actionable_insights=sig_insights,
        ))
    else:
        report.category_scores.append(CategoryScore(
            category="PERFUMER_ATTRIBUTION",
            score=0.0,
            label=_label_score(0.0),
            detail="No perfumer/house data — identify the perfumer for portfolio priors",
        ))

    # ── Stage 5: Economic Plausibility (COG) ──────────────────────
    if spec.retail_price_usd > 0 and spec.estimated_materials_pct:
        cost_res = analyze_cost_of_goods(
            target_name=spec.name,
            retail_price_100ml=spec.retail_price_usd,
            materials_pct=spec.estimated_materials_pct,
            tier=spec.price_tier or "luxury_niche",
            concentrate_pct=spec.concentration_pct,
        )
        report.cost_result = cost_res

        cost_insights = []
        if cost_res.implausible_materials:
            cost_insights.append(f"Implausible quantities: {', '.join(cost_res.implausible_materials)}")
        cost_insights.append(f"Budget utilization: {cost_res.budget_utilization:.0f}%")

        report.category_scores.append(CategoryScore(
            category="ECONOMIC_PLAUSIBILITY",
            score=cost_res.score,
            label=_label_score(cost_res.score),
            detail=f"COG ${cost_res.cog_estimate:.2f} vs budget ${cost_res.raw_material_budget:.2f}",
            actionable_insights=cost_insights,
        ))
    else:
        report.category_scores.append(CategoryScore(
            category="ECONOMIC_PLAUSIBILITY",
            score=0.0,
            label=_label_score(0.0),
            detail="No price/materials data — add retail price and estimated material %",
        ))

    # ── Stage 6: ODT Perceptual Consistency ───────────────────────
    if spec.community_votes:
        odt_res = analyze_odor_thresholds(
            target_name=spec.name,
            note_votes=spec.community_votes,
            total_reviewers=spec.total_reviewers,
            concentrate_pct=spec.concentration_pct,
        )
        report.odt_result = odt_res

        odt_insights = []
        if odt_res.materials_above_threshold:
            odt_insights.append(f"Above threshold: {', '.join(odt_res.materials_above_threshold[:5])}")
        if odt_res.materials_below_threshold:
            odt_insights.append(f"Below threshold: {', '.join(odt_res.materials_below_threshold[:5])}")

        report.category_scores.append(CategoryScore(
            category="PERCEPTUAL_CONSISTENCY",
            score=odt_res.score,
            label=_label_score(odt_res.score),
            detail=f"{len(odt_res.materials_above_threshold)} materials above ODT, "
                   f"{len(odt_res.materials_below_threshold)} below",
            actionable_insights=odt_insights,
        ))
    else:
        report.category_scores.append(CategoryScore(
            category="PERCEPTUAL_CONSISTENCY",
            score=0.0,
            label=_label_score(0.0),
            detail="No community vote data — add note voting data from Fragrantica/Parfumo",
        ))

    # ── Stage 7: Material Interactions ────────────────────────────
    material_posteriors = {
        m.name: m.posterior for m in bayesian.materials
    } if bayesian.materials else {}

    confirmed_names = [m.name for m in bayesian.confirmed] if bayesian.confirmed else []
    probable_names = [m.name for m in bayesian.probable] if bayesian.probable else []

    if material_posteriors:
        interaction_res = analyze_material_interactions(
            target_name=spec.name,
            material_posteriors=material_posteriors,
            confirmed_materials=confirmed_names,
            probable_materials=probable_names,
        )
        report.interaction_result = interaction_res

        int_insights = []
        for tmpl in interaction_res.template_matches:
            int_insights.append(f"Template match: {tmpl.template_name} (score={tmpl.match_score:.2f})")
        for a, b, mult in interaction_res.strongest_interactions[:3]:
            int_insights.append(f"Strong link: {a} → {b} (×{mult:.2f})")

        report.category_scores.append(CategoryScore(
            category="MATERIAL_INTERACTIONS",
            score=interaction_res.score,
            label=_label_score(interaction_res.score),
            detail=f"{len(interaction_res.effects)} interaction effects, "
                   f"{len(interaction_res.template_matches)} template matches",
            actionable_insights=int_insights,
        ))
    else:
        report.category_scores.append(CategoryScore(
            category="MATERIAL_INTERACTIONS",
            score=0.0,
            label=_label_score(0.0),
            detail="No materials identified — no interactions to analyze",
        ))

    # ── Stage 8: Vapor Pressure / Sillage Prediction ──────────────
    declared_pyramid = {
        "top": spec.top_notes,
        "heart": spec.heart_notes,
        "base": spec.base_notes,
    }
    if material_posteriors:
        vp_res = analyze_vapor_pressure(
            target_name=spec.name,
            material_posteriors=material_posteriors,
            declared_pyramid=declared_pyramid,
            concentrate_pct=spec.concentration_pct,
        )
        report.vp_result = vp_res

        vp_insights = []
        if vp_res.misclassified_materials:
            vp_insights.append(f"Volatility mismatch: {', '.join(vp_res.misclassified_materials[:4])}")
        vp_insights.append(f"Sillage index: {vp_res.sillage_index:.1f}/100")

        report.category_scores.append(CategoryScore(
            category="SILLAGE_PREDICTION",
            score=vp_res.score,
            label=_label_score(vp_res.score),
            detail=f"{len(vp_res.top_note_materials)} top / {len(vp_res.heart_note_materials)} heart / "
                   f"{len(vp_res.base_note_materials)} base materials classified",
            actionable_insights=vp_insights,
        ))
    else:
        report.category_scores.append(CategoryScore(
            category="SILLAGE_PREDICTION",
            score=0.0,
            label=_label_score(0.0),
            detail="No materials identified — cannot predict sillage",
        ))

    # ── Stage 9: Temporal Consistency ─────────────────────────────
    if material_posteriors:
        temporal_res = analyze_temporal_consistency(
            target_name=spec.name,
            material_posteriors=material_posteriors,
            declared_pyramid=declared_pyramid,
        )
        report.temporal_result = temporal_res

        temporal_insights = []
        if temporal_res.inconsistent_materials:
            temporal_insights.append(f"Temporal mismatch: {', '.join(temporal_res.inconsistent_materials[:4])}")
        temporal_insights.append(f"Consistent: {len(temporal_res.consistent_materials)}, "
                                  f"Inconsistent: {len(temporal_res.inconsistent_materials)}")

        report.category_scores.append(CategoryScore(
            category="TEMPORAL_CONSISTENCY",
            score=temporal_res.score,
            label=_label_score(temporal_res.score),
            detail=f"{len(temporal_res.consistent_materials)} materials in correct volatility window",
            actionable_insights=temporal_insights,
        ))
    else:
        report.category_scores.append(CategoryScore(
            category="TEMPORAL_CONSISTENCY",
            score=0.0,
            label=_label_score(0.0),
            detail="No materials identified — cannot assess temporal consistency",
        ))

    # ── Stage 10: Supply Chain / Captive Availability ─────────────
    if spec.perfumer and spec.year > 0 and material_posteriors:
        captive_res = analyze_captive_availability(
            target_name=spec.name,
            perfumer=spec.perfumer,
            year=spec.year,
            material_posteriors=material_posteriors,
            confirmed_materials=confirmed_names,
        )
        report.captive_result = captive_res

        captive_insights = []
        if captive_res.impossible_materials:
            captive_insights.append(f"Cross-house captives: {', '.join(captive_res.impossible_materials[:3])}")
        if captive_res.anachronistic_materials:
            captive_insights.append(f"Post-launch materials: {', '.join(captive_res.anachronistic_materials[:3])}")
        captive_insights.append(f"Employer: {captive_res.employer_at_launch}")

        report.category_scores.append(CategoryScore(
            category="SUPPLY_CHAIN_PLAUSIBILITY",
            score=captive_res.score,
            label=_label_score(captive_res.score),
            detail=f"Employer: {captive_res.employer_at_launch}, "
                   f"{len(captive_res.plausible_materials)} plausible, "
                   f"{len(captive_res.impossible_materials)} impossible",
            actionable_insights=captive_insights,
        ))
    else:
        report.category_scores.append(CategoryScore(
            category="SUPPLY_CHAIN_PLAUSIBILITY",
            score=0.0,
            label=_label_score(0.0),
            detail="Need perfumer name and launch year for supply chain analysis",
        ))

    # ── Stage 11: Regulatory Timeline ─────────────────────────────
    if spec.year > 0 and material_posteriors:
        regulatory_res = analyze_regulatory_timeline(
            target_name=spec.name,
            fragrance_year=spec.year,
            material_posteriors=material_posteriors,
            concentrate_pct=spec.concentration_pct,
            known_reformulation_year=spec.known_reformulation_year,
        )
        report.regulatory_result = regulatory_res

        reg_insights = []
        if regulatory_res.prohibited_at_launch:
            reg_insights.append(f"Prohibited at launch: {', '.join(regulatory_res.prohibited_at_launch[:3])}")
        if regulatory_res.restricted_since_launch:
            reg_insights.append(f"Restricted since launch: {', '.join(regulatory_res.restricted_since_launch[:4])}")
        reg_insights.append(f"Amendments at launch: {', '.join(regulatory_res.applicable_amendments)}")

        report.category_scores.append(CategoryScore(
            category="REGULATORY_CONSISTENCY",
            score=regulatory_res.score,
            label=_label_score(regulatory_res.score),
            detail=f"{len(regulatory_res.always_compliant)} compliant, "
                   f"{len(regulatory_res.prohibited_at_launch)} prohibited at launch",
            actionable_insights=reg_insights,
        ))
    else:
        report.category_scores.append(CategoryScore(
            category="REGULATORY_CONSISTENCY",
            score=0.0,
            label=_label_score(0.0),
            detail="Need launch year for regulatory timeline analysis",
        ))

    # ── Stage 12: Molecular Weight / Physicochemical Coherence ────
    if material_posteriors:
        mw_res = analyze_mw_distribution(
            target_name=spec.name,
            material_posteriors=material_posteriors,
            fragrance_family=spec.fragrance_family,
            confirmed_materials=confirmed_names,
        )
        report.mw_result = mw_res

        mw_insights = []
        mw_insights.append(f"Detected family: {mw_res.detected_family}, mean MW: {mw_res.mean_mw:.1f}")
        if mw_res.outlier_materials:
            mw_insights.append(f"MW outliers: {', '.join(mw_res.outlier_materials[:4])}")

        report.category_scores.append(CategoryScore(
            category="PHYSICOCHEMICAL_COHERENCE",
            score=mw_res.score,
            label=_label_score(mw_res.score),
            detail=f"Family: {mw_res.detected_family}, MW {mw_res.mean_mw:.0f}±{mw_res.std_mw:.0f}, "
                   f"logP {mw_res.mean_logp:.1f}",
            actionable_insights=mw_insights,
        ))
    else:
        report.category_scores.append(CategoryScore(
            category="PHYSICOCHEMICAL_COHERENCE",
            score=0.0,
            label=_label_score(0.0),
            detail="No materials identified — cannot compute MW distribution",
        ))

    # ── Final material consolidation ──────────────────────────────
    # Merge Bayesian posteriors with interaction adjustments
    final_posteriors = {}
    if report.interaction_result and report.interaction_result.adjusted_posteriors:
        final_posteriors = dict(report.interaction_result.adjusted_posteriors)
    elif bayesian.materials:
        final_posteriors = {m.name.lower(): m.posterior for m in bayesian.materials}

    for m in bayesian.materials:
        key = m.name.lower().strip()
        report.final_materials[m.name] = {
            "posterior": final_posteriors.get(key, m.posterior),
            "tier": m.tier.value,
            "concentration_pct": m.concentration_best,
            "sources": sorted(m.source_types_seen),
            "n_sources": m.n_sources,
            "corroboration": m.corroboration_factor,
        }

    # ── Optimization recommendations ──────────────────────────────
    for cs in sorted(report.category_scores, key=lambda c: c.score):
        if cs.score < 60:
            report.optimization_targets.append(
                f"[{cs.category}] Score {cs.score:.0f}/100 ({cs.label}) — "
                + (cs.actionable_insights[0] if cs.actionable_insights else "add more data")
            )

    report.elapsed_seconds = time.time() - start
    return report


# ══════════════════════════════════════════════════════════════════════
# Report formatting
# ══════════════════════════════════════════════════════════════════════

def format_pipeline_report(report: PipelineReport) -> str:
    """Format the full pipeline report with category-based scores."""
    lines = []
    w = 80  # Line width

    lines.append("═" * w)
    lines.append(f"  RECONSTRUCTION PIPELINE: {report.target_name}")
    lines.append(f"  {report.timestamp}  |  Elapsed: {report.elapsed_seconds:.2f}s")
    lines.append("═" * w)
    lines.append("")

    # ── Category Scorecard ────────────────────────────────────────
    lines.append("┌──────────────────────────────┬───────┬─────────────────────────────────────┐")
    lines.append("│ CATEGORY                     │ SCORE │ ASSESSMENT                          │")
    lines.append("├──────────────────────────────┼───────┼─────────────────────────────────────┤")

    for cs in sorted(report.category_scores, key=lambda c: c.score, reverse=True):
        cat = cs.category[:28].ljust(28)
        score = f"{cs.score:5.1f}".rjust(5)
        # Truncate label to fit
        label = cs.label[:35].ljust(35)
        lines.append(f"│ {cat} │ {score} │ {label} │")

    lines.append("├──────────────────────────────┼───────┼─────────────────────────────────────┤")
    overall = report.overall_confidence
    lines.append(f"│ {'OVERALL CONFIDENCE':28} │ {overall:5.1f} │ {_label_score(overall):35} │")
    lines.append("└──────────────────────────────┴───────┴─────────────────────────────────────┘")
    lines.append("")

    # ── Category Details ──────────────────────────────────────────
    lines.append("── CATEGORY DETAILS ──")
    for cs in report.category_scores:
        lines.append(f"\n  [{cs.category}] {cs.score:.1f}/100 — {cs.label}")
        lines.append(f"  {cs.detail}")
        for insight in cs.actionable_insights:
            lines.append(f"    • {insight}")

    # ── Bayesian Material Table ───────────────────────────────────
    if report.bayesian_result:
        lines.append("")
        lines.append("── MATERIAL RECONSTRUCTION ──")
        lines.append(format_reconstruction_report(report.bayesian_result))

    # ── Optimization Targets ──────────────────────────────────────
    if report.optimization_targets:
        lines.append("")
        lines.append("── OPTIMIZATION TARGETS (weakest categories) ──")
        for i, target in enumerate(report.optimization_targets, 1):
            lines.append(f"  {i}. {target}")

    # ── What Would Improve Each Category ──────────────────────────
    lines.append("")
    lines.append("── HOW TO IMPROVE EACH CATEGORY ──")
    improvement_map = {
        "BAYESIAN_POSTERIOR": "Add GC-MS peaks, patent formulas, or perfumer disclosures",
        "ALLERGEN_EVIDENCE": "Photograph allergen box list; check IFRA amendments for batch year",
        "ALLERGEN_CHEMISTRY": "Provide allergen ratios (citronellol:geraniol, etc.) from literature",
        "PERFUMER_ATTRIBUTION": "Identify perfumer; study their other formulas for material patterns",
        "ECONOMIC_PLAUSIBILITY": "Estimate material concentrations; check retail price consistency",
        "PERCEPTUAL_CONSISTENCY": "Collect community note votes from Fragrantica/Parfumo/Basenotes",
        "MATERIAL_INTERACTIONS": "Confirm key materials to unlock co-occurrence intelligence",
        "SILLAGE_PREDICTION": "Add material posteriors; check declared pyramid notes vs volatility",
        "TEMPORAL_CONSISTENCY": "Verify note pyramid order matches material VP class (top/heart/base)",
        "SUPPLY_CHAIN_PLAUSIBILITY": "Identify perfumer employer; check for rival-house captive conflicts",
        "REGULATORY_CONSISTENCY": "Provide launch year + concentrate%; check IFRA amendment compliance",
        "PHYSICOCHEMICAL_COHERENCE": "Specify fragrance family for MW/logP distribution validation",
    }
    for cs in sorted(report.category_scores, key=lambda c: c.score):
        improvement = improvement_map.get(cs.category, "Add more data")
        lines.append(f"  {cs.category}: {cs.score:.0f} → {improvement}")

    lines.append("")
    lines.append("═" * w)

    return "\n".join(lines)


def pipeline_report_to_dict(report: PipelineReport) -> dict:
    """Convert pipeline report to JSON-serializable dict."""
    return {
        "target_name": report.target_name,
        "timestamp": report.timestamp,
        "elapsed_seconds": report.elapsed_seconds,
        "overall_confidence": report.overall_confidence,
        "category_scores": [
            {
                "category": cs.category,
                "score": cs.score,
                "label": cs.label,
                "detail": cs.detail,
                "actionable_insights": cs.actionable_insights,
            }
            for cs in report.category_scores
        ],
        "final_materials": report.final_materials,
        "optimization_targets": report.optimization_targets,
        "weakest_category": report.weakest_category.category if report.weakest_category else None,
        "strongest_category": report.strongest_category.category if report.strongest_category else None,
    }
