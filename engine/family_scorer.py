"""Family-aware formula scoring — applies different axis weights per fragrance family.

Each fragrance family has different priorities. A soliflore shouldn't be penalized
for low versatility or stacking depth — those are inherent to the concept. An
oriental shouldn't be penalized for low photorealism — it's a fantasy composition.

Usage:
    from engine.family_scorer import FamilyAwareScorer

    scorer = FamilyAwareScorer()
    scores = scorer.score(formula_vector)  # auto-detects family

    # Or specify explicitly:
    scores = scorer.score(formula_vector, family="soliflore")

    # Compare generic vs family-aware:
    comparison = scorer.compare(formula_vector)
"""

from __future__ import annotations

from dataclasses import dataclass

from engine.optimizer.models import FormulaVector, ObjectiveWeights
from engine.optimizer.scoring import FormulaScorer
from engine.synergy_graph import SynergyGraph

# ═══════════════════════════════════════════════════════════════════════════════
# FAMILY WEIGHT PRESETS
# ═══════════════════════════════════════════════════════════════════════════════
#
# Each preset defines which scoring axes matter most for a given fragrance family.
# Weights range 0.0-1.0; higher = more influence on the geometric composite.
#
# Design principles:
#   - Families that inherently lack an axis (soliflore → versatility) get low weight
#   - Families where an axis is defining (oriental → longevity) get high weight
#   - Defaults are kept for axes that are equally relevant across families
# ═══════════════════════════════════════════════════════════════════════════════

FAMILY_WEIGHT_PRESETS: dict[str, ObjectiveWeights] = {
    # ── Soliflore — single-flower celebration ──
    # Priorities: photorealism (botanical fidelity), hedonic (beauty), texture (smooth)
    # De-emphasized: versatility (one flower), stacking_depth (one subject), longevity (flowers are ephemeral)
    "soliflore": ObjectiveWeights(
        longevity=0.5,       # flowers are fleeting — don't penalize
        sillage=0.9,         # the flower should project
        synergy=0.6,         # materials should harmonize around the flower
        luxury=0.6,          # moderate — soliflores can be luxurious or humble
        texture=0.9,         # smooth, silky, petal-soft — crucial
        stacking_depth=0.3,  # single subject, not layered architecture
        skin_performance=0.5,  # moderate — some intimacy, not the point
        hedonic=0.9,         # beauty is the whole point
        perceptual_clarity=0.7,  # clean reading of the flower
        photorealism=1.0,    # must smell like the real flower — defining axis
    ),

    # ── Cologne / Fresh — bright, citrus, effervescent ──
    # Priorities: sillage (projection), photorealism (smells real), perceptual_clarity (clean reading)
    # De-emphasized: longevity (colognes are intentionally short), luxury (not about opulence), stacking_depth (simple)
    "cologne": ObjectiveWeights(
        longevity=0.3,       # colognes are meant to be ephemeral
        sillage=1.0,         # projection is everything
        synergy=0.5,         # moderate — simple citrus blends
        luxury=0.4,          # colognes are refreshing, not opulent
        texture=0.6,         # crisp, clean, not heavily textured
        stacking_depth=0.3,  # simple architecture
        skin_performance=0.4,  # not about skin intimacy
        hedonic=0.7,         # should be pleasant
        perceptual_clarity=0.9,  # must read clean and clear
        photorealism=0.9,    # should smell like real citrus/herbs
    ),
    "fresh": "cologne",  # alias — fresh is the category, cologne is the style

    # ── Fougère — lavender + coumarin + oakmoss, structured aromatic ──
    # Priorities: stacking_depth (architectural), synergy (triad must work), longevity (built to last)
    # De-emphasized: photorealism (abstract accord), hedonic (more structural than beautiful)
    "fougere": ObjectiveWeights(
        longevity=0.9,       # fougères are built to last
        sillage=0.7,         # moderate projection — not a cologne
        synergy=0.9,         # the lavender-coumarin-oakmoss triad must harmonize
        luxury=0.6,          # can be humble (barbershop) or refined (niche)
        texture=0.8,         # the dry-herbal texture is characteristic
        stacking_depth=0.9,  # the layered architecture IS the fougère
        skin_performance=0.6,  # moderate
        hedonic=0.5,         # structural, not pretty — beauty comes from order
        perceptual_clarity=0.6,  # moderate — fougères can be busy
        photorealism=0.5,    # abstract accord, not botanical realism
    ),

    # ── Oriental — rich, warm, resinous, opulent ──
    # Priorities: longevity (defining trait), luxury (opulence), texture (round, enveloping), hedonic (pleasurable)
    # De-emphasized: photorealism (fantasy), perceptual_clarity (dense and complex)
    "oriental": ObjectiveWeights(
        longevity=1.0,       # the defining trait — orientals must last
        sillage=0.7,         # moderate to high, but not the focus
        synergy=0.7,         # resins + spices + woods must harmonize
        luxury=1.0,          # opulence is the point
        texture=1.0,         # round, creamy, enveloping — defining
        stacking_depth=0.8,  # layered warmth architecture
        skin_performance=0.8,  # orientals should hug the skin
        hedonic=0.9,         # must be deeply pleasurable
        perceptual_clarity=0.3,  # orientals are dense, not clean
        photorealism=0.3,    # fantasy composition, not botanical
    ),

    # ── Chypre — bergamot + labdanum + oakmoss, sophisticated, dry ──
    # Priorities: longevity, stacking_depth (bergamot-to-oakmoss arc), texture (dry-sophisticated)
    # De-emphasized: photorealism (abstract), hedonic (intellectual, not pretty)
    "chypre": ObjectiveWeights(
        longevity=0.9,       # chypres are built on substantial bases
        sillage=0.6,         # moderate — sophistication over projection
        synergy=0.8,         # the bergamot-labdanum-oakmoss spine must work
        luxury=0.8,          # chypres are inherently sophisticated
        texture=0.9,         # the dry, elegant texture is defining
        stacking_depth=0.9,  # the top-to-base arc IS the chypre
        skin_performance=0.7,  # should wear close and personal
        hedonic=0.5,         # intellectual, not crowd-pleasing
        perceptual_clarity=0.5,  # moderate — chypres have complexity
        photorealism=0.4,    # abstract composition
    ),

    # ── Woody — cedar, sandalwood, vetiver, dry-grainy ──
    # Priorities: longevity, texture (grain/dryness), stacking_depth
    # De-emphasized: photorealism (abstract wood, not a tree), hedonic (structural)
    "woody": ObjectiveWeights(
        longevity=0.9,       # woods persist
        sillage=0.6,         # moderate — woods are often close
        synergy=0.7,         # wood blends should harmonize
        luxury=0.7,          # depends on wood quality (sandalwood vs cedar)
        texture=0.9,         # the grain, dryness, creaminess — defining
        stacking_depth=0.8,  # layered wood architecture
        skin_performance=0.7,  # woods often wear well on skin
        hedonic=0.5,         # structural, not floral-beautiful
        perceptual_clarity=0.6,  # moderate
        photorealism=0.4,    # abstract wood, not a tree
    ),

    # ── Amber — warm, resinous, vanillic ──
    # Priorities: longevity, luxury (resins = opulence), hedonic (warm = pleasurable), texture (smooth)
    # De-emphasized: photorealism (fantasy), perceptual_clarity (dense)
    "amber": ObjectiveWeights(
        longevity=0.9,       # resins and vanilla persist
        sillage=0.7,         # moderate to high
        synergy=0.7,         # the amber accord must cohere
        luxury=0.9,          # resins are luxury materials
        texture=0.9,         # smooth, round, enveloping
        stacking_depth=0.7,  # moderate layering
        skin_performance=0.7,  # warm on skin
        hedonic=0.8,         # warm-fuzzy = inherently pleasurable
        perceptual_clarity=0.4,  # amber is dense and opaque
        photorealism=0.3,    # fantasy accord
    ),

    # ── Floral — rose, jasmine, muguet, abstract bouquet ──
    # Priorities: hedonic (flowers = beauty), sillage (florals should bloom), photorealism
    # De-emphasized: stacking_depth (often simple), longevity (florals can be fleeting)
    "floral": ObjectiveWeights(
        longevity=0.6,       # florals vary — some fleeting, some lasting
        sillage=0.9,         # florals should project and bloom
        synergy=0.7,         # bouquet harmony
        luxury=0.7,          # florals can be luxurious or humble
        texture=0.8,         # petal-soft, silky
        stacking_depth=0.5,  # often simple architecture
        skin_performance=0.6,  # moderate
        hedonic=1.0,         # beauty is the entire point
        perceptual_clarity=0.7,  # clean floral reading
        photorealism=0.8,    # should smell like flowers
    ),

    # ── Iris (powdery / crystalline) — sub-style of Floral ──
    # Similar to floral but with higher texture and powder emphasis
    "iris_powdery": ObjectiveWeights(
        longevity=0.7,       # iris bases last
        sillage=0.7,         # iris is often intimate
        synergy=0.7,         # ionone harmony
        luxury=0.9,          # iris = luxury material
        texture=1.0,         # powder, suede, butter — the defining axis
        stacking_depth=0.6,  # moderate
        skin_performance=0.8,  # iris is a skin-scent material
        hedonic=0.8,         # powdery = pleasurable
        perceptual_clarity=0.6,  # moderate — powder softens edges
        photorealism=0.7,    # orris/iris realism
    ),
    "iris_crystalline": ObjectiveWeights(
        longevity=0.7,
        sillage=0.7,
        synergy=0.7,
        luxury=0.9,
        texture=0.9,         # crisp, transparent, not heavy powder
        stacking_depth=0.6,
        skin_performance=0.8,
        hedonic=0.8,
        perceptual_clarity=0.8,  # crystalline = transparent
        photorealism=0.7,
    ),

    # ── Green — galbanum, violet leaf, cut grass ──
    # Priorities: photorealism (must smell like living plant), perceptual_clarity (crisp), sillage
    # De-emphasized: luxury (green is humble), hedonic (often sharp), longevity (green tops are fleeting)
    "green": ObjectiveWeights(
        longevity=0.5,       # green tops are inherently fleeting
        sillage=0.9,         # green notes project sharply
        synergy=0.6,         # moderate
        luxury=0.4,          # green is humble and natural, not opulent
        texture=0.7,         # crisp, sharp, sometimes wet
        stacking_depth=0.5,  # simpler architecture
        skin_performance=0.5,  # moderate
        hedonic=0.5,         # green can be sharp and challenging
        perceptual_clarity=0.9,  # must read crisp and clean
        photorealism=1.0,    # must smell like the living plant — defining
    ),

    # ── Leather — IBQ, birch tar, suede ──
    # Priorities: longevity, texture (tactile leather), stacking_depth
    # De-emphasized: photorealism (abstract), hedonic (leather is divisive)
    "leather": ObjectiveWeights(
        longevity=0.9,       # leather bases persist
        sillage=0.6,         # moderate — often close-wearing
        synergy=0.7,         # the leather accord must cohere
        luxury=0.7,          # leather can be luxurious
        texture=0.9,         # the tactile leather feel — defining
        stacking_depth=0.8,  # layered leather architecture
        skin_performance=0.8,  # leather and skin are a natural pairing
        hedonic=0.4,         # leather is divisive, not universally pleasant
        perceptual_clarity=0.6,  # moderate
        photorealism=0.4,    # abstract accord
    ),

    # ── Skin Scent / Musk — intimate, close-wearing ──
    # Priorities: skin_performance (the whole point), longevity, texture (smooth, skin-like)
    # De-emphasized: sillage (intentionally close), photorealism (abstract)
    "skin_scent": ObjectiveWeights(
        longevity=0.9,       # skin scents should linger subtly
        sillage=0.3,         # intentionally close — low projection is the point
        synergy=0.6,         # materials should blend seamlessly
        luxury=0.6,          # can be humble or refined
        texture=0.9,         # smooth, skin-like, seamless — defining
        stacking_depth=0.5,  # simpler architecture
        skin_performance=1.0,  # the whole point — must perform on skin
        hedonic=0.7,         # should be pleasant and comfortable
        perceptual_clarity=0.6,  # moderate
        photorealism=0.4,    # abstract — "your skin but better" is not photorealistic
    ),
    "musky": "skin_scent",  # alias

    # ── Gourmand — edible, sweet, vanillic ──
    # Priorities: hedonic (pleasure), longevity (sweet notes persist), luxury (often indulgent)
    # De-emphasized: photorealism (fantasy food), perceptual_clarity (dense)
    "gourmand": ObjectiveWeights(
        longevity=0.9,       # sweet notes are tenacious
        sillage=0.7,         # moderate to high
        synergy=0.7,         # the food accord must be convincing
        luxury=0.8,          # gourmands often feel indulgent
        texture=0.8,         # creamy, smooth, edible
        stacking_depth=0.6,  # moderate
        skin_performance=0.7,  # sweet notes wear well
        hedonic=1.0,         # pleasure is the entire point
        perceptual_clarity=0.4,  # gourmands are dense and complex
        photorealism=0.3,    # fantasy food, not literal
    ),

    # ── Spicy — pepper, clove, cinnamon, cardamom ──
    # Priorities: longevity, sillage, texture (the spice tingle)
    # De-emphasized: photorealism (spice accords are abstract)
    "spicy": ObjectiveWeights(
        longevity=0.8,       # spices persist
        sillage=0.9,         # spice projects sharply
        synergy=0.6,         # moderate
        luxury=0.6,          # can be humble or exotic
        texture=0.8,         # the warm, tingling spice texture
        stacking_depth=0.6,  # moderate
        skin_performance=0.6,  # moderate
        hedonic=0.6,         # spices are warming but can be challenging
        perceptual_clarity=0.6,  # moderate
        photorealism=0.5,    # spice accords are abstract blends
    ),

    # ── Classical — traditional, balanced ──
    # Balanced weights — the Carles ideal
    "classical": ObjectiveWeights(
        longevity=0.8,
        sillage=0.8,
        synergy=0.8,
        luxury=0.7,
        texture=0.8,
        stacking_depth=0.8,
        skin_performance=0.7,
        hedonic=0.7,
        perceptual_clarity=0.7,
        photorealism=0.6,
    ),

    # ── Linear — even evaporation, modern transparent ──
    # Priorities: texture, perceptual_clarity, photorealism
    # De-emphasized: stacking_depth (intentionally flat arc)
    "linear": ObjectiveWeights(
        longevity=0.7,
        sillage=0.7,
        synergy=0.7,
        luxury=0.6,
        texture=0.9,         # smooth, even — defining
        stacking_depth=0.3,  # intentionally flat — not a weakness
        skin_performance=0.8,  # linear fragrances often wear well
        hedonic=0.7,
        perceptual_clarity=0.9,  # must read clean across the arc
        photorealism=0.7,
    ),
    "aromatic_fougere": "fougere",
    "fougere_classical": "fougere",
    "citrus_classical": "cologne",
    "citrus_aromatic": "cologne",
    "floral_soliflore": "soliflore",
    "floral_bouquet": "floral",
    "floral_white": "floral",
    "floral_muguet": "soliflore",
    "floral_carnation": "floral",
    "floral_powdery": "floral",
    "floral_green": "green",
    "floral_aldehydic": "floral",
    "chypre_classical": "chypre",
    "chypre_floral": "chypre",
    "chypre_fruity": "chypre",
    "chypre_green": "chypre",
    "chypre_leathery": "chypre",
    "oriental_classical": "oriental",
    "oriental_soft": "amber",
    "oriental_floral": "oriental",
}

# Resolve aliases into flat dict
_RESOLVED: dict[str, ObjectiveWeights] = {}
for _key, _val in FAMILY_WEIGHT_PRESETS.items():
    if isinstance(_val, str):
        _RESOLVED[_key] = _RESOLVED.get(_val) or FAMILY_WEIGHT_PRESETS[_val]
    else:
        _RESOLVED[_key] = _val

# Default weights matching the original ObjectiveWeights defaults
DEFAULT_WEIGHTS = ObjectiveWeights()


def get_family_weights(family: str) -> ObjectiveWeights:
    """Return ObjectiveWeights for a given fragrance family/style.

    Args:
        family: Style name from FormulaScorer.detect_style() output.
                E.g., 'soliflore', 'fougere', 'oriental', 'fresh', etc.

    Returns:
        ObjectiveWeights configured for that family, or DEFAULT_WEIGHTS if unknown.
    """
    key = family.lower().replace(" ", "_").replace("-", "_")
    if key in _RESOLVED:
        return _RESOLVED[key]
    if "." in key:
        stem = key.split(".", 1)[0]
        if stem in _RESOLVED:
            return _RESOLVED[stem]
    return DEFAULT_WEIGHTS


# ═══════════════════════════════════════════════════════════════════════════════
# FAMILY-AWARE SCORER
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class FamilyScoreResult:
    """Result from family-aware scoring."""
    family: str
    family_confidence: float
    generic_scores: dict[str, object]
    family_scores: dict[str, object]
    generic_total: float
    family_total: float
    delta: float  # family_total - generic_total

    @property
    def improved(self) -> bool:
        return self.delta > 0


class FamilyAwareScorer:
    """Formula scorer that applies family-specific axis weights.

    Detects the formula's style/family, then scores with weights tuned to that
    family's priorities. A soliflore won't be penalized for low stacking_depth.
    A cologne won't be penalized for low longevity.

    Usage:
        scorer = FamilyAwareScorer()
        scores = scorer.score(fv)           # auto-detect family
        scores = scorer.score(fv, "fougere")  # explicit family
        comparison = scorer.compare(fv)       # generic vs family-aware
    """

    def __init__(self, synergy_graph: SynergyGraph | None = None):
        self._synergy_graph = synergy_graph
        self._base_scorer = FormulaScorer(synergy_graph=synergy_graph)

    def detect_family(self, fv: FormulaVector) -> tuple[str, float]:
        """Detect the formula's fragrance family/style.

        Returns:
            (family_name, confidence) tuple.
        """
        fingerprint = self._base_scorer.style_fingerprint(fv)
        dominant = fingerprint.get("dominant_style", "classical")
        primary = fingerprint.get("primary_candidate", {})
        confidence = primary.get("confidence", 0.5) if isinstance(primary, dict) else 0.5

        # Map detected style to a family weight key
        style_lower = str(dominant).lower().replace(" ", "_").replace("-", "_")
        if style_lower in _RESOLVED:
            return style_lower, float(confidence)

        # Try category candidates as fallback
        cat_candidates = fingerprint.get("category_candidates", [])
        if isinstance(cat_candidates, list) and cat_candidates:
            first_cat = cat_candidates[0]
            if isinstance(first_cat, dict):
                cat_style = str(first_cat.get("style", "")).lower().replace(" ", "_")
                if cat_style in _RESOLVED:
                    return cat_style, float(first_cat.get("confidence", 0.5))

        return "classical", 0.3

    def score(self, fv: FormulaVector, family: str | None = None) -> dict[str, object]:
        """Score a formula with family-specific weights.

        Args:
            fv: FormulaVector to score.
            family: Optional explicit family name. If None, auto-detected.

        Returns:
            Score dict (same format as FormulaScorer.score()) with
            family-specific geometric/arithmetic totals.
            Adds '_family' and '_family_confidence' keys.
        """
        if family is None:
            family, confidence = self.detect_family(fv)
        else:
            confidence = 1.0

        weights = get_family_weights(family)

        # Score with family-specific weights
        scorer = FormulaScorer(weights=weights, synergy_graph=self._synergy_graph)
        scores = scorer.score(fv)

        # Tag with family info
        scores["_family"] = family
        scores["_family_confidence"] = round(confidence, 3)
        scores["_family_weights"] = weights.as_dict()

        return scores

    def compare(self, fv: FormulaVector, family: str | None = None) -> FamilyScoreResult:
        """Score with both generic and family-specific weights for comparison.

        Returns:
            FamilyScoreResult with both score sets and the delta.
        """
        if family is None:
            family, confidence = self.detect_family(fv)
        else:
            confidence = 1.0

        # Generic scoring (default weights)
        generic_scorer = FormulaScorer(weights=DEFAULT_WEIGHTS, synergy_graph=self._synergy_graph)
        generic_scores = generic_scorer.score(fv)

        # Family-specific scoring
        weights = get_family_weights(family)
        family_scorer = FormulaScorer(weights=weights, synergy_graph=self._synergy_graph)
        family_scores = family_scorer.score(fv)

        return FamilyScoreResult(
            family=family,
            family_confidence=confidence,
            generic_scores=generic_scores,
            family_scores=family_scores,
            generic_total=float(generic_scores.get("geometric_total", 0)),
            family_total=float(family_scores.get("geometric_total", 0)),
            delta=round(float(family_scores.get("geometric_total", 0))
                       - float(generic_scores.get("geometric_total", 0)), 1),
        )
