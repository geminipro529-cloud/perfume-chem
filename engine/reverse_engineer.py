"""Reverse Engineering Engine — Evidence-weighted probabilistic formula reconstruction.

Reconstructs probable perfume formulas from heterogeneous evidence sources
(GC-MS data, patents, allergen declarations, community reviews, perfumer
disclosures, IFRA limits) using Bayesian posterior updating with
corroboration multipliers for cross-source agreement.

Mathematical framework
──────────────────────
For each candidate material M_i and independent evidence items E_1..E_n:

    P(M_i | E_1..E_n) ∝ P(M_i) · ∏_k P(E_k | M_i)

Where:
  P(M_i)       = prior probability (base rate from industry data)
  P(E_k | M_i) = likelihood of observing evidence k if M_i present

Corroboration bonus (user requirement — "duplicated information is likely true"):
  When N ≥ 2 independent source *types* claim the same material,
  posterior is multiplied by a corroboration factor:
    corr_factor = 1.0 + 0.3 * (N_types - 1)   (capped at 3.0×)

Output tiers:
  CONFIRMED   — posterior ≥ 0.80
  PROBABLE    — 0.50 ≤ posterior < 0.80
  SPECULATIVE — posterior < 0.50

Usage:
    pool = EvidencePool("Dior Homme Intense")
    pool.add(EvidenceItem(source_type="gcms", material="Iso E Super",
             confidence=0.95, concentration_pct=17.0))
    pool.add(EvidenceItem(source_type="allergen", material="Alpha-Isomethyl Ionone",
             confidence=0.90))
    result = reverse_engineer(pool)
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


# ── Constants ──────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Source type reliability ranges (from research)
SOURCE_RELIABILITY: dict[str, tuple[float, float]] = {
    "gcms":        (0.85, 0.98),   # GC-MS analytical data
    "allergen":    (0.80, 0.95),   # EU mandatory allergen declaration
    "ifra":        (0.80, 0.90),   # IFRA ceiling (negative evidence mainly)
    "patent":      (0.40, 0.75),   # Patent example formulas
    "perfumer":    (0.40, 0.70),   # Perfumer interviews / disclosures
    "community":   (0.45, 0.65),   # Aggregated community review consensus
    "review":      (0.15, 0.35),   # Individual user review
    "marketing":   (0.20, 0.40),   # Brand marketing / official note pyramid
    "expert":      (0.50, 0.75),   # Expert reconstruction / blog analysis
}

# Likelihood ratios P(E|M_present) / P(E|M_absent) per source type
# Used for Bayesian updating: posterior_odds = prior_odds × LR
LIKELIHOOD_RATIOS: dict[str, dict[str, float]] = {
    "gcms":      {"present": 0.95, "absent": 0.03},   # high TPR, low FPR
    "allergen":  {"present": 0.95, "absent": 0.10},   # mandatory if above threshold
    "patent":    {"present": 0.50, "absent": 0.25},   # patents cover many examples
    "perfumer":  {"present": 0.90, "absent": 0.03},   # perfumers rarely lie about use
    "community": {"present": 0.65, "absent": 0.12},   # crowd signal, noisy
    "review":    {"present": 0.40, "absent": 0.20},   # individual, unreliable
    "marketing": {"present": 0.55, "absent": 0.20},   # marketing inflates naturals
    "expert":    {"present": 0.70, "absent": 0.10},   # expert analysis
    "ifra":      {"present": 0.85, "absent": 0.15},   # ceiling data
}

# Corroboration matrix: bonus when N independent source TYPES agree
# "duplicated information is likely true"
CORROBORATION_BASE = 0.30      # +30% per additional independent source type
CORROBORATION_CAP  = 3.0       # maximum multiplier

# Cross-type corroboration quality weights (some combos more meaningful)
CORROBORATION_QUALITY: dict[tuple[str, str], float] = {
    ("gcms", "allergen"):   2.2,   # analytical + regulatory = very strong
    ("gcms", "perfumer"):   2.5,   # analytical + expert confirmation
    ("gcms", "patent"):     2.8,   # analytical + disclosed formula
    ("allergen", "community"): 1.4, # regulatory + perceptual
    ("patent", "perfumer"): 1.8,   # disclosed formula + expert
    ("community", "perfumer"): 1.5, # crowd + expert agreement
}

# Prior probability base rates for common material categories
MATERIAL_BASE_RATES: dict[str, float] = {
    # Workhorse materials — very common in fine fragrance
    "hedione":            0.60,
    "iso e super":        0.55,
    "galaxolide":         0.45,
    "benzyl salicylate":  0.50,
    "linalool":           0.75,
    "linalyl acetate":    0.55,
    "coumarin":           0.35,
    "ethylene brassylate": 0.30,
    "ambroxan":           0.30,
    "cashmeran":          0.20,
    # Less common — specialty or niche
    "alpha irone":        0.08,
    "cis-3-hexenol":      0.15,
    "indole":             0.20,
    "guaiacol":           0.10,
    "oakmoss":            0.05,
    "isobutyl quinoline":  0.08,
    "oud":                0.02,
}
DEFAULT_BASE_RATE = 0.15  # default prior for unknown materials

# Confidence tier thresholds
TIER_CONFIRMED   = 0.80
TIER_PROBABLE    = 0.50


class ConfidenceTier(str, Enum):
    CONFIRMED   = "CONFIRMED"
    PROBABLE    = "PROBABLE"
    SPECULATIVE = "SPECULATIVE"


# ── Data classes ──────────────────────────────────────────────────────

@dataclass
class EvidenceItem:
    """Single piece of evidence about a material's presence in a fragrance."""
    source_type: str                        # key into SOURCE_RELIABILITY
    material: str                           # claimed material name
    confidence: float = 0.0                 # source-specific confidence 0..1
    concentration_pct: Optional[float] = None  # estimated % of concentrate
    concentration_range: Optional[tuple[float, float]] = None  # (low, high) %
    ifra_ceiling_pct: Optional[float] = None   # IFRA max for this material
    raw_text: str = ""                      # original evidence text
    source_url: str = ""                    # URL / reference

    def __post_init__(self):
        self.source_type = self.source_type.lower().strip()
        if self.source_type not in SOURCE_RELIABILITY:
            raise ValueError(
                f"Unknown source_type '{self.source_type}'. "
                f"Valid: {list(SOURCE_RELIABILITY.keys())}"
            )
        self.confidence = max(0.0, min(1.0, self.confidence))


@dataclass
class MaterialHypothesis:
    """Accumulated evidence and posterior probability for one material."""
    name: str
    prior: float = DEFAULT_BASE_RATE
    posterior: float = DEFAULT_BASE_RATE
    evidence: list[EvidenceItem] = field(default_factory=list)
    source_types_seen: set[str] = field(default_factory=set)
    corroboration_factor: float = 1.0
    concentration_estimates: list[float] = field(default_factory=list)
    concentration_range: tuple[float, float] = (0.0, 100.0)
    ifra_ceiling: Optional[float] = None
    tier: ConfidenceTier = ConfidenceTier.SPECULATIVE

    @property
    def n_sources(self) -> int:
        return len(self.source_types_seen)

    @property
    def concentration_best(self) -> Optional[float]:
        """Inverse-variance weighted concentration estimate."""
        if not self.concentration_estimates:
            return None
        # Weight by source reliability: GC-MS estimates are tighter
        # For simplicity, use median of estimates (robust to outliers)
        sorted_est = sorted(self.concentration_estimates)
        n = len(sorted_est)
        if n % 2 == 1:
            return sorted_est[n // 2]
        return (sorted_est[n // 2 - 1] + sorted_est[n // 2]) / 2

    def update_tier(self):
        if self.posterior >= TIER_CONFIRMED:
            self.tier = ConfidenceTier.CONFIRMED
        elif self.posterior >= TIER_PROBABLE:
            self.tier = ConfidenceTier.PROBABLE
        else:
            self.tier = ConfidenceTier.SPECULATIVE


@dataclass
class ReconstructedFormula:
    """Final output of the reverse engineering pipeline."""
    target_name: str
    materials: list[MaterialHypothesis] = field(default_factory=list)
    accord_family: str = ""
    total_evidence_items: int = 0
    conflict_flags: list[str] = field(default_factory=list)

    @property
    def confirmed(self) -> list[MaterialHypothesis]:
        return [m for m in self.materials if m.tier == ConfidenceTier.CONFIRMED]

    @property
    def probable(self) -> list[MaterialHypothesis]:
        return [m for m in self.materials if m.tier == ConfidenceTier.PROBABLE]

    @property
    def speculative(self) -> list[MaterialHypothesis]:
        return [m for m in self.materials if m.tier == ConfidenceTier.SPECULATIVE]

    @property
    def actionable(self) -> bool:
        """A reconstruction is actionable when ≥80% of mass is CONFIRMED."""
        confirmed_mass = sum(
            m.concentration_best or 0 for m in self.confirmed
        )
        total_mass = sum(
            m.concentration_best or 0 for m in self.materials
            if m.concentration_best is not None
        )
        if total_mass == 0:
            return False
        return (confirmed_mass / total_mass) >= 0.80


# ── Evidence Pool ─────────────────────────────────────────────────────

class EvidencePool:
    """Collects evidence items and tracks per-material hypotheses."""

    def __init__(self, target_name: str):
        self.target_name = target_name
        self.items: list[EvidenceItem] = []
        self._hypotheses: dict[str, MaterialHypothesis] = {}

    def add(self, item: EvidenceItem):
        """Add a single evidence item to the pool."""
        self.items.append(item)
        key = _normalize_material(item.material)
        if key not in self._hypotheses:
            prior = _lookup_prior(key)
            self._hypotheses[key] = MaterialHypothesis(
                name=item.material, prior=prior, posterior=prior
            )
        hyp = self._hypotheses[key]
        hyp.evidence.append(item)
        hyp.source_types_seen.add(item.source_type)
        if item.concentration_pct is not None:
            hyp.concentration_estimates.append(item.concentration_pct)
        if item.concentration_range is not None:
            lo, hi = item.concentration_range
            hyp.concentration_range = (
                max(hyp.concentration_range[0], lo),
                min(hyp.concentration_range[1], hi),
            )
        if item.ifra_ceiling_pct is not None:
            if hyp.ifra_ceiling is None:
                hyp.ifra_ceiling = item.ifra_ceiling_pct
            else:
                hyp.ifra_ceiling = min(hyp.ifra_ceiling, item.ifra_ceiling_pct)

    def add_many(self, items: list[EvidenceItem]):
        for item in items:
            self.add(item)

    @property
    def hypotheses(self) -> dict[str, MaterialHypothesis]:
        return self._hypotheses

    def __len__(self) -> int:
        return len(self.items)


# ── Core Bayesian Engine ──────────────────────────────────────────────

def _normalize_material(name: str) -> str:
    """Normalize material name for matching."""
    return name.lower().strip().replace("-", " ").replace("_", " ")


def _lookup_prior(material_key: str) -> float:
    """Look up base rate prior for a material."""
    return MATERIAL_BASE_RATES.get(material_key, DEFAULT_BASE_RATE)


def _bayesian_update(prior: float, evidence: list[EvidenceItem]) -> float:
    """Sequential Bayesian updating: P(M|E1..En) ∝ P(M) · ∏ P(Ek|M).

    Uses odds form for numerical stability:
        posterior_odds = prior_odds × ∏ likelihood_ratio_k

    Where LR_k = P(E_k|M_present) / P(E_k|M_absent), scaled by item confidence.
    """
    if not evidence:
        return prior

    # Work in log-odds for numerical stability
    if prior <= 0:
        prior = 1e-6
    if prior >= 1:
        prior = 1 - 1e-6
    log_odds = math.log(prior / (1 - prior))

    for item in evidence:
        lr = _likelihood_ratio(item)
        if lr > 0:
            log_odds += math.log(lr)

    # Convert back to probability
    posterior = 1.0 / (1.0 + math.exp(-log_odds))
    return max(0.0, min(1.0, posterior))


def _likelihood_ratio(item: EvidenceItem) -> float:
    """Compute likelihood ratio for a single evidence item.

    LR = P(E|M_present) / P(E|M_absent)

    Scaled by item's own confidence — lower confidence items
    produce LR closer to 1.0 (less informative).
    """
    lr_data = LIKELIHOOD_RATIOS.get(item.source_type)
    if lr_data is None:
        return 1.0  # uninformative

    p_present = lr_data["present"]
    p_absent = lr_data["absent"]

    # Scale by confidence: at confidence=0, LR→1 (uninformative)
    # at confidence=1, use full LR
    effective_present = item.confidence * p_present + (1 - item.confidence) * 0.5
    effective_absent = item.confidence * p_absent + (1 - item.confidence) * 0.5

    if effective_absent <= 0:
        effective_absent = 1e-6

    return effective_present / effective_absent


def _compute_corroboration(hyp: MaterialHypothesis) -> float:
    """Compute corroboration multiplier based on independent source types.

    User requirement: "giving extra attention to the information found
    that is duplicated since that information is likely true."

    When N ≥ 2 independent source types confirm the same material:
        factor = 1.0 + 0.30 × (N_types - 1), capped at 3.0

    Additionally, certain source-type pairs have quality bonuses
    (e.g., GC-MS + allergen = very strong cross-validation).
    """
    types = hyp.source_types_seen
    n = len(types)
    if n < 2:
        return 1.0

    # Base corroboration from source diversity
    factor = 1.0 + CORROBORATION_BASE * (n - 1)

    # Quality bonuses for especially meaningful pairings
    type_list = sorted(types)
    for i in range(len(type_list)):
        for j in range(i + 1, len(type_list)):
            pair = (type_list[i], type_list[j])
            reverse = (type_list[j], type_list[i])
            quality = CORROBORATION_QUALITY.get(
                pair, CORROBORATION_QUALITY.get(reverse, 0.0)
            )
            if quality > 0:
                # Add fractional bonus from high-quality pairs
                factor += (quality - 1.0) * 0.15

    return min(factor, CORROBORATION_CAP)


def _detect_conflicts(pool: EvidencePool) -> list[str]:
    """Flag materials where evidence sources contradict each other."""
    flags = []
    for key, hyp in pool.hypotheses.items():
        # Check for contradictory evidence (some say present, some say absent)
        positive = [e for e in hyp.evidence if e.confidence > 0.5]
        negative_implicit = []

        # Check IFRA ceiling violations
        if hyp.ifra_ceiling is not None and hyp.concentration_estimates:
            for est in hyp.concentration_estimates:
                if est > hyp.ifra_ceiling:
                    flags.append(
                        f"IFRA CONFLICT: {hyp.name} estimated at {est:.1f}% "
                        f"but IFRA ceiling is {hyp.ifra_ceiling:.1f}%"
                    )

        # Check wildly divergent concentration estimates
        if len(hyp.concentration_estimates) >= 2:
            lo = min(hyp.concentration_estimates)
            hi = max(hyp.concentration_estimates)
            if hi > 0 and (hi / max(lo, 0.01)) > 5.0:
                flags.append(
                    f"CONCENTRATION SPREAD: {hyp.name} estimates range "
                    f"{lo:.1f}%–{hi:.1f}% (>{5}× spread)"
                )

        # Source type disagreement — high combined confidence in opposite directions
        if len(hyp.source_types_seen) >= 2:
            conf_values = [e.confidence for e in hyp.evidence]
            if conf_values:
                mean_conf = sum(conf_values) / len(conf_values)
                variance = sum((c - mean_conf) ** 2 for c in conf_values) / len(conf_values)
                if variance > 0.08:  # high disagreement
                    flags.append(
                        f"SOURCE DISAGREEMENT: {hyp.name} — evidence confidence "
                        f"variance {variance:.3f} across {len(hyp.source_types_seen)} source types"
                    )

    return flags


# ── Main Reconstruction Function ─────────────────────────────────────

def reverse_engineer(pool: EvidencePool) -> ReconstructedFormula:
    """Run the full reverse engineering pipeline on an evidence pool.

    Pipeline stages:
      1. Bayesian posterior update for each material hypothesis
      2. Corroboration multiplier for cross-source agreement
      3. IFRA ceiling enforcement on concentration estimates
      4. Conflict detection across contradictory sources
      5. Tier assignment (CONFIRMED / PROBABLE / SPECULATIVE)
      6. Concentration estimate consolidation
      7. Sort by posterior (most confident first)
    """
    result = ReconstructedFormula(
        target_name=pool.target_name,
        total_evidence_items=len(pool),
    )

    for key, hyp in pool.hypotheses.items():
        # Stage 1: Bayesian update
        hyp.posterior = _bayesian_update(hyp.prior, hyp.evidence)

        # Stage 2: Corroboration multiplier
        hyp.corroboration_factor = _compute_corroboration(hyp)
        # Apply corroboration: boost posterior toward 1.0
        if hyp.corroboration_factor > 1.0:
            boosted = hyp.posterior * hyp.corroboration_factor
            # Sigmoid-like capping: don't exceed 0.995
            hyp.posterior = min(boosted, 0.995)

        # Stage 3: IFRA ceiling enforcement
        if hyp.ifra_ceiling is not None:
            hyp.concentration_range = (
                hyp.concentration_range[0],
                min(hyp.concentration_range[1], hyp.ifra_ceiling),
            )
            # Clamp estimates to ceiling
            hyp.concentration_estimates = [
                min(c, hyp.ifra_ceiling) for c in hyp.concentration_estimates
            ]

        # Stage 5: Tier assignment
        hyp.update_tier()

        result.materials.append(hyp)

    # Stage 4: Conflict detection (runs across all hypotheses)
    result.conflict_flags = _detect_conflicts(pool)

    # Stage 7: Sort by posterior descending
    result.materials.sort(key=lambda m: m.posterior, reverse=True)

    return result


# ── Descriptor → Material Mapping ─────────────────────────────────────
# Shared by parse_note_pyramid and parse_review_consensus.
# Each descriptor maps to [(material_name, mapping_confidence), ...]

_DESCRIPTOR_MAP: dict[str, list[tuple[str, float]]] = {
    # Citrus
    "bergamot":     [("Bergamot FCF", 0.70)],
    "lemon":        [("Citral", 0.40), ("D-Limonene", 0.50)],
    "orange":       [("Blood Orange Sicilian", 0.40), ("D-Limonene", 0.50)],
    "grapefruit":   [("Grapefruit FCF", 0.50), ("Methyl Pamplemousse", 0.30)],
    "mandarin":     [("Red Mandarin EO", 0.55)],
    "lime":         [("D-Limonene", 0.40)],
    "citrus":       [("D-Limonene", 0.50), ("Bergamot FCF", 0.35)],
    # Floral
    "rose":         [("Geraniol", 0.45), ("Citronellol", 0.40), ("Phenylethyl Alcohol", 0.50)],
    "jasmine":      [("Hedione", 0.60), ("Cis-Jasmone", 0.25), ("Indole", 0.20)],
    "iris":         [("Alpha-Isomethyl Ionone", 0.65), ("Alpha Irone 10%", 0.30)],
    "orris":        [("Alpha-Isomethyl Ionone", 0.60), ("Alpha Irone 10%", 0.35)],
    "violet":       [("Alpha-Isomethyl Ionone", 0.55), ("Parmavert", 0.25)],
    "lily of the valley": [("Hydroxycitronellal", 0.50), ("Lilyreal ND", 0.30), ("Bourgeonal", 0.25)],
    "muguet":       [("Hydroxycitronellal", 0.45), ("Lilyreal ND", 0.35)],
    "gardenia":     [("DBCA", 0.40), ("Benzyl Salicylate", 0.35)],
    "tuberose":     [("Indole", 0.30), ("Methyl Benzoate", 0.25)],
    "neroli":       [("Neroli EO", 0.65)],
    "ylang":        [("Ylang Ylang EO", 0.60)],
    "freesia":      [("Freesia HDI", 0.45)],
    "magnolia":     [("Linalool", 0.40), ("Citronellol", 0.30)],
    # Woody
    "sandalwood":   [("Javanol", 0.30), ("Ebanol", 0.25), ("Bacdanol", 0.25)],
    "cedar":        [("Cedarwood EO", 0.50), ("Iso E Super", 0.40)],
    "cedarwood":    [("Cedarwood EO", 0.55), ("Iso E Super", 0.35)],
    "vetiver":      [("Vetiver EO", 0.60), ("Vetival", 0.25)],
    "patchouli":    [("Patchouli EO", 0.70)],
    "oud":          [("Oud FTEC", 0.40)],
    "wood":         [("Iso E Super", 0.45), ("Vertofix Coeur", 0.25), ("Timberol", 0.20)],
    "woody":        [("Iso E Super", 0.45), ("Vertofix Coeur", 0.25), ("Timberol", 0.20)],
    # Amber/Balsamic
    "amber":        [("Ambrox Super 30%", 0.35), ("Labdanum", 0.25)],
    "ambergris":    [("Ambrox Super 30%", 0.55)],
    "vanilla":      [("Vanillin", 0.55), ("Ethyl Vanillin", 0.30)],
    "tonka":        [("Coumarin", 0.65)],
    "benzoin":      [("Benzoin Resinoid 50%", 0.60)],
    "labdanum":     [("Labdanum", 0.55)],
    "incense":      [("Olibanum EO", 0.50)],
    "frankincense": [("Olibanum EO", 0.60)],
    # Musk
    "musk":         [("Galaxolide 80%", 0.40), ("Ethylene Brassylate", 0.30)],
    "white musk":   [("Galaxolide 80%", 0.45), ("Ethylene Brassylate", 0.35)],
    "skin":         [("Iso E Super", 0.35), ("Galaxolide 80%", 0.30)],
    # Spicy
    "cardamom":     [("Cardamom EO", 0.05)],
    "pepper":       [("Pink Pepper EO", 0.45)],
    "pink pepper":  [("Pink Pepper EO", 0.60)],
    "saffron":      [("Ethyl Safranate", 0.50)],
    "cinnamon":     [("Cinnamaldehyde", 0.55)],
    # Green/Herbal
    "lavender":     [("Lavender EO", 0.65)],
    "green":        [("Cis-3-Hexenol", 0.30), ("Leafovert", 0.25), ("Dynascone", 0.15)],
    "grass":        [("Leafovert", 0.40), ("Cis-3-Hexenol", 0.35)],
    "galbanum":     [("Dynascone", 0.35)],
    # Gourmand
    "caramel":      [("Ethyl Maltol", 0.50)],
    "chocolate":    [("Cocoa FTEC", 0.35)],
    "coffee":       [("Coffee FTEC", 0.40)],
    "honey":        [("Phenylacetic Acid", 0.30)],
    "almond":       [("Benzaldehyde", 0.50)],
    # Leather/Animalic
    "leather":      [("Suederal", 0.35), ("IBQ (Isobutyl Quinoline)", 0.25), ("Birch Tar", 0.20)],
    "suede":        [("Suederal", 0.50), ("Vetival", 0.25)],
    # Aquatic/Ozonic
    "marine":       [("Calone 1%", 0.40), ("Scentenal", 0.25)],
    "ozonic":       [("Scentenal", 0.35), ("Calone 1%", 0.30)],
    "aquatic":      [("Calone 1%", 0.40)],
    # Fruity
    "peach":        [("Gamma-Decalactone", 0.50)],
    "coconut":      [("Gamma-Nonalactone", 0.50)],
    "tropical":     [("Paradisamide", 0.30)],
    "blackcurrant": [("Blackcurrant FTEC", 0.40), ("Paradisamide", 0.25)],
    "cassis":       [("Blackcurrant FTEC", 0.45), ("Paradisamide", 0.20)],
    "pineapple":    [("Allyl Amyl Glycolate", 0.40)],
    # Powdery
    "powder":       [("Alpha-Isomethyl Ionone", 0.40), ("Coumarin", 0.30)],
    "powdery":      [("Alpha-Isomethyl Ionone", 0.40), ("Coumarin", 0.30)],
}


# ── Evidence Parsers ──────────────────────────────────────────────────

def parse_allergen_list(allergen_text: str) -> list[EvidenceItem]:
    """Parse EU allergen declaration text into evidence items.

    Input: INCI-style text like "Linalool, Limonene, Coumarin, Citronellol"
    Output: EvidenceItem per allergen with high confidence (regulatory data).

    The 26 mandatory EU allergens that must be declared:
    """
    # EU 26 mandatory allergens → common perfume material mappings
    allergen_materials = {
        "linalool": "Linalool",
        "limonene": "D-Limonene",
        "citronellol": "Citronellol",
        "geraniol": "Geraniol",
        "coumarin": "Coumarin",
        "citral": "Citral",
        "eugenol": "Eugenol",
        "isoeugenol": "Isoeugenol",
        "cinnamal": "Cinnamaldehyde",
        "cinnamaldehyde": "Cinnamaldehyde",
        "cinnamyl alcohol": "Cinnamyl Alcohol",
        "hydroxycitronellal": "Hydroxycitronellal",
        "alpha-isomethyl ionone": "Alpha-Isomethyl Ionone",
        "benzyl benzoate": "Benzyl Benzoate",
        "benzyl salicylate": "Benzyl Salicylate",
        "benzyl alcohol": "Benzyl Alcohol",
        "benzyl cinnamate": "Benzyl Cinnamate",
        "farnesol": "Farnesol",
        "butylphenyl methylpropional": "Lilial",
        "hexyl cinnamal": "Hexyl Cinnamal",
        "amyl cinnamal": "Amyl Cinnamal",
        "amylcinnamyl alcohol": "Amylcinnamyl Alcohol",
        "anise alcohol": "Anise Alcohol",
        "methyl 2-octynoate": "Methyl Heptin Carbonate",
        "evernia prunastri": "Oakmoss",
        "evernia furfuracea": "Treemoss",
    }

    items = []
    # Split on commas, semicolons, or newlines
    parts = [p.strip().lower() for p in
             allergen_text.replace(";", ",").replace("\n", ",").split(",")]

    for part in parts:
        if not part:
            continue
        # Match against known allergens
        for allergen_key, material_name in allergen_materials.items():
            if allergen_key in part or part in allergen_key:
                items.append(EvidenceItem(
                    source_type="allergen",
                    material=material_name,
                    confidence=0.90,
                    raw_text=part,
                ))
                break

    return items


def parse_note_pyramid(
    top: list[str] | None = None,
    heart: list[str] | None = None,
    base: list[str] | None = None,
    source_type: str = "marketing",
) -> list[EvidenceItem]:
    """Parse a note pyramid (top/heart/base) into evidence items.

    Note names are marketing-level descriptors, not chemical names.
    Confidence is moderate — note pyramids are often aspirational.
    """
    items = []
    for notes, section in [(top, "top"), (heart, "heart"), (base, "base")]:
        if not notes:
            continue
        for note_name in notes:
            key = note_name.lower().strip()
            if key in _DESCRIPTOR_MAP:
                for material, conf in _DESCRIPTOR_MAP[key]:
                    items.append(EvidenceItem(
                        source_type=source_type,
                        material=material,
                        confidence=conf * 0.8,  # scale down — marketing is aspirational
                        raw_text=f"{note_name} ({section})",
                    ))

    return items


def parse_review_consensus(
    notes_with_votes: dict[str, float],
    total_reviewers: int = 100,
) -> list[EvidenceItem]:
    """Parse community note-voting data into evidence items.

    Input: {"iris": 0.72, "wood": 0.65, "musk": 0.45, ...}
           where values are fraction of reviewers who detected the note.

    Descriptor names are resolved to probable chemical materials using
    the same descriptor→material map as parse_note_pyramid. Confidence
    from the Condorcet model is combined with descriptor→material mapping
    confidence to produce calibrated evidence items.
    """
    # Reuse the descriptor map (defined inside parse_note_pyramid — extract it)
    descriptor_map = _DESCRIPTOR_MAP

    items = []
    for note_name, vote_fraction in notes_with_votes.items():
        # Condorcet-adjusted confidence: higher with more agreement
        n = max(int(total_reviewers * vote_fraction), 1)

        if vote_fraction >= 0.50:
            condorcet_conf = min(0.95, 0.50 + 0.10 * math.log(max(n, 1)))
        elif vote_fraction >= 0.25:
            condorcet_conf = 0.30 + vote_fraction * 0.40
        else:
            condorcet_conf = vote_fraction * 0.80

        key = note_name.lower().strip()
        if key in descriptor_map:
            # Map to chemical materials with combined confidence
            for material, mapping_conf in descriptor_map[key]:
                items.append(EvidenceItem(
                    source_type="community",
                    material=material,
                    confidence=condorcet_conf * mapping_conf,
                    raw_text=(f"{vote_fraction*100:.0f}% of {total_reviewers} "
                              f"reviewers detect '{note_name}' → {material}"),
                ))
        else:
            # Unknown descriptor — keep as-is with lower confidence
            items.append(EvidenceItem(
                source_type="community",
                material=note_name,
                confidence=condorcet_conf * 0.3,
                raw_text=(f"{vote_fraction*100:.0f}% of {total_reviewers} "
                          f"reviewers detect '{note_name}' (unmapped descriptor)"),
            ))

    return items


def parse_patent_formula(
    materials_pct: dict[str, float],
    patent_id: str = "",
) -> list[EvidenceItem]:
    """Parse a patent example formula into evidence items.

    Input: {"Hedione": 18.5, "Iso E Super": 12.0, "Coumarin": 3.5, ...}
           where values are % of concentrate.
    """
    items = []
    for material, pct in materials_pct.items():
        items.append(EvidenceItem(
            source_type="patent",
            material=material,
            confidence=0.55,  # patents describe examples, not necessarily the commercial product
            concentration_pct=pct,
            raw_text=f"Patent {patent_id}: {material} at {pct:.1f}%",
            source_url=patent_id,
        ))
    return items


# ── Report Formatting ─────────────────────────────────────────────────

def format_reconstruction_report(result: ReconstructedFormula) -> str:
    """Format the reconstruction result as a readable report."""
    lines = []
    lines.append(f"═══ REVERSE ENGINEERING: {result.target_name} ═══")
    lines.append(f"Evidence items processed: {result.total_evidence_items}")
    lines.append(f"Materials identified:     {len(result.materials)}")
    lines.append(f"  CONFIRMED:   {len(result.confirmed)}")
    lines.append(f"  PROBABLE:    {len(result.probable)}")
    lines.append(f"  SPECULATIVE: {len(result.speculative)}")
    lines.append(f"Actionable:              {'YES' if result.actionable else 'NO — need more CONFIRMED evidence'}")
    lines.append("")

    # Conflict warnings
    if result.conflict_flags:
        lines.append("⚠ CONFLICTS DETECTED:")
        for flag in result.conflict_flags:
            lines.append(f"  • {flag}")
        lines.append("")

    # Material table
    hdr = f"{'Material':<30} {'Tier':<12} {'Post':<6} {'Corr':<5} {'Conc%':<8} {'Sources':<6} {'Evidence'}"
    lines.append(hdr)
    lines.append("─" * len(hdr))

    for m in result.materials:
        conc = f"{m.concentration_best:.1f}" if m.concentration_best is not None else "—"
        sources_str = str(m.n_sources)
        evidence_summary = ", ".join(sorted(m.source_types_seen))
        corr_str = f"×{m.corroboration_factor:.1f}" if m.corroboration_factor > 1.0 else "—"

        lines.append(
            f"{m.name:<30} {m.tier.value:<12} {m.posterior:<6.3f} {corr_str:<5} "
            f"{conc:<8} {sources_str:<6} {evidence_summary}"
        )

    lines.append("")

    # Detailed evidence chain for CONFIRMED materials
    if result.confirmed:
        lines.append("── CONFIRMED Materials — Evidence Chains ──")
        for m in result.confirmed:
            lines.append(f"\n  {m.name} (P={m.posterior:.3f}, {m.n_sources} source types)")
            for e in m.evidence:
                lines.append(f"    [{e.source_type.upper()}] conf={e.confidence:.2f}: {e.raw_text}")
            if m.concentration_best is not None:
                lines.append(f"    → Concentration estimate: {m.concentration_best:.1f}%")
            if m.ifra_ceiling is not None:
                lines.append(f"    → IFRA ceiling: {m.ifra_ceiling:.1f}%")

    return "\n".join(lines)


def reconstruction_to_formula_vector(result: ReconstructedFormula) -> dict:
    """Convert a reconstruction to FormulaVector-compatible dicts.

    Returns dict with 'ingredients' and 'dilutions' suitable for
    FormulaVector(ingredients=..., dilutions=...).

    Only includes CONFIRMED and PROBABLE materials.
    Uses concentration_best for amounts (scaled to 10mL batch).
    """
    ingredients = {}
    dilutions = {}
    batch_mL = 10.0

    for m in result.materials:
        if m.tier == ConfidenceTier.SPECULATIVE:
            continue
        if m.concentration_best is None:
            continue

        # Convert concentrate % to µL in a 10mL batch
        # Assume ~15% concentrate in EdP → concentrate volume ≈ 1.5 mL = 1500 µL
        concentrate_uL = 1500.0
        amount_uL = (m.concentration_best / 100.0) * concentrate_uL

        if amount_uL > 0:
            ingredients[m.name] = amount_uL
            dilutions[m.name] = 1.0  # assume neat unless evidence says otherwise

    return {"ingredients": ingredients, "dilutions": dilutions}


# ── CLI Entry Point ───────────────────────────────────────────────────

def _demo():
    """Demo: reconstruct Dior Homme Intense from mixed evidence."""
    pool = EvidencePool("Dior Homme Intense (demo)")

    # GC-MS evidence (analytical)
    pool.add(EvidenceItem("gcms", "Alpha-Isomethyl Ionone", 0.95,
                          concentration_pct=17.8,
                          raw_text="Strong AIMI peak, RT 28.3 min, NIST match 94%"))
    pool.add(EvidenceItem("gcms", "Iso E Super", 0.92,
                          concentration_pct=8.0,
                          raw_text="IES peak cluster, RT 32.1 min"))
    pool.add(EvidenceItem("gcms", "Hedione", 0.88,
                          concentration_pct=15.0,
                          raw_text="Methyl dihydrojasmonate, RT 25.7 min"))
    pool.add(EvidenceItem("gcms", "Coumarin", 0.90,
                          concentration_pct=6.3,
                          raw_text="Coumarin peak, RT 22.4 min"))

    # EU allergen declarations
    pool.add_many(parse_allergen_list(
        "Alpha-Isomethyl Ionone, Linalool, Coumarin, "
        "Limonene, Citronellol, Geraniol, Hydroxycitronellal"
    ))

    # Fragrantica note pyramid
    pool.add_many(parse_note_pyramid(
        top=["lavender", "iris", "bergamot"],
        heart=["iris", "cedar", "amber"],
        base=["leather", "vanilla", "vetiver"],
        source_type="marketing",
    ))

    # Community consensus
    pool.add_many(parse_review_consensus({
        "iris": 0.82,
        "powder": 0.71,
        "wood": 0.65,
        "amber": 0.58,
        "leather": 0.42,
        "cocoa": 0.38,
    }, total_reviewers=2500))

    # Perfumer disclosure
    pool.add(EvidenceItem("perfumer", "Alpha-Isomethyl Ionone", 0.85,
                          raw_text="François Demachy: 'a massive iris accord'"))
    pool.add(EvidenceItem("perfumer", "Iso E Super", 0.70,
                          raw_text="Interview reference to 'woody molecular depth'"))

    result = reverse_engineer(pool)
    print(format_reconstruction_report(result))
    return result


if __name__ == "__main__":
    _demo()
