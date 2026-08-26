"""Aromachemical Expansion Recommender.

Analyses the current inventory against the full material intelligence database
and recommends the best chemicals to buy next, scored across multiple axes:

1. Character Coverage — fills gaps in the 13-D olfactive radar
2. Synergy Unlock — materials that create the most new synergy edges
3. Cross-Adaptation Diversity — materials that open new receptor groups
4. Versatility — how many formula archetypes a material serves
5. Dose-Response Intelligence — materials with known Hill/character data
6. ODT Coverage — materials that improve headspace modelling accuracy
7. Anosmia Redundancy — materials that back up anosmia-prone inventory items
8. Structural Gap Fill — gap_detector severity mapping

Each candidate gets a composite score (geometric mean of normalised axes)
and a purchase-priority tier.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from engine.dose_response import CHARACTER_SHIFT_DATA, HILL_PARAMS
from engine.ingredient_intelligence import (
    DIMENSIONS,
    MaterialProfile,
    character_distance,
    get_all_profiles,
    get_profile,
)
from engine.inventory_parser import InventoryMaterial, parse_inventory
from engine.material_identity import catalog_identity_key
from engine.name_utils import normalize_name
from engine.odor_thresholds import ODT_DATA
from engine.pipeline.natural_absolute_decomposition import get_composite_metadata
from engine.psychophysics import CROSS_ADAPTATION_GROUPS, GENETIC_ANOSMIA
from engine.synergy_graph import SynergyGraph

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Weights for composite score (geometric mean with exponents)
AXIS_WEIGHTS = {
    "character_coverage": 1.5,
    "synergy_unlock": 1.2,
    "cross_adaptation": 1.0,
    "versatility": 1.0,
    "intelligence_depth": 0.8,
    "anosmia_redundancy": 0.6,
    "structural_gap": 0.5,
}

# Formula archetypes from synergy_graph musk affinity — used for versatility
ARCHETYPES = [
    "woody", "floral", "fresh", "oriental", "green",
    "citrus", "chypre", "gourmand", "aquatic", "leather",
    "iris", "rose", "oud", "fougere", "amber",
]

# Role versatility scores — materials that play multiple roles are more useful
ROLE_VERSATILITY = {
    "character": 1.0,
    "modifier": 1.2,   # modifiers fit into more formulas
    "volume": 1.1,
    "fixative": 1.0,
    "radiance": 1.1,
    "bridge": 1.3,     # bridges are the most versatile
    "trace": 0.7,      # trace materials are niche
}

# Materials the user explicitly wants to avoid buying (can be extended)
EXCLUDE_MATERIALS: set[str] = set()

# Maximum recommendations to return
DEFAULT_TOP_N = 30

# Narrow equivalence corrections for labels that are not distinct purchase
# opportunities.  These are identity/label corrections, not broad olfactory
# substitution rules: Heliotropin is piperonal (FAO/JECFA synonym), Cedamber is
# a legacy misspelling/duplicate of IFF Cedramber, and the Ambrox stock profile
# is merely a preparation of Ambrox Super.
_IDENTITY_EQUIVALENCE = {
    "heliotropin": "heliotropal",
    "piperonal": "heliotropal",
    "cedamber": "cedramber",
    "ambrox super 33% dep etoh": "ambrox super",
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ExpansionCandidate:
    """A material that the user does NOT own, scored for purchase priority."""
    name: str
    profile: MaterialProfile

    # Axis scores (0-100 each, before weighting)
    character_coverage_score: float = 0.0
    synergy_unlock_score: float = 0.0
    cross_adaptation_score: float = 0.0
    versatility_score: float = 0.0
    intelligence_depth_score: float = 0.0
    anosmia_redundancy_score: float = 0.0
    structural_gap_score: float = 0.0

    # Composite
    composite_score: float = 0.0
    tier: str = ""  # "essential", "high_value", "useful", "niche", "low_priority"

    # Diagnostics
    reasons: list[str] = field(default_factory=list)
    fills_dimensions: list[str] = field(default_factory=list)
    new_synergies: list[str] = field(default_factory=list)
    new_adaptation_groups: list[str] = field(default_factory=list)
    backs_up_anosmic: list[str] = field(default_factory=list)
    identity_key: str = ""
    purchase_mode: str = "range_extension"
    closest_owned: str = ""
    closest_owned_distance: float | None = None
    functional_overlap_multiplier: float = 1.0
    modelling_authority: str = ""
    modelling_authority_multiplier: float = 1.0


@dataclass
class ExpansionReport:
    """Full expansion analysis output."""
    candidates: list[ExpansionCandidate]
    inventory_size: int
    candidates_evaluated: int
    dimension_coverage: dict[str, float]  # current coverage per dimension (0-1)
    weakest_dimensions: list[str]
    adaptation_group_coverage: dict[str, int]  # group → count of owned materials
    missing_groups: list[str]
    anosmia_exposure: float  # fraction of inventory at anosmia risk
    diagnostics: list[str]
    ranking_authority: str = "MODELLED_RANGE_GAP_NOT_PURCHASE_ORDER"
    inventory_scope: str = "AVAILABLE_NON_SOLVENT_STOCK"
    excluded_owned_aliases: tuple[str, ...] = ()
    excluded_existing_unavailable: tuple[str, ...] = ()
    model_limitations: tuple[str, ...] = (
        "Supplier availability and delivered price are not verified by this model.",
        "IFRA suitability must be checked against the intended product category before purchase or use.",
        "Character-space similarity is a screening aid, not proof of olfactory interchangeability.",
    )


# ---------------------------------------------------------------------------
# Scoring functions
# ---------------------------------------------------------------------------

def _profile_for_inventory_item(item: InventoryMaterial) -> MaterialProfile | None:
    """Resolve an inventory display/stock label to its canonical profile."""

    return get_profile(item.identity_name or item.name) or get_profile(item.name)


def _identity_key(name: str, profile: MaterialProfile | None = None) -> str:
    """Return a purchase-level identity key, independent of stock preparation."""

    profile_name = profile.name if profile is not None else name
    key = catalog_identity_key(profile_name) or normalize_name(profile_name)
    key = normalize_name(key)
    return _IDENTITY_EQUIVALENCE.get(key, key)


def _inventory_context(
    inventory_path: str = "inventory.txt",
) -> tuple[list[InventoryMaterial], list[InventoryMaterial]]:
    path = Path(inventory_path)
    available = parse_inventory(
        path,
        unique=True,
        include_solvents=False,
        include_unavailable=False,
    )
    all_records = parse_inventory(
        path,
        unique=False,
        # Include all categories for identity exclusion. A useful structural
        # material may be filed under carriers (for example Myristic Acid), and
        # must never be recommended back merely because of its shelf heading.
        include_solvents=True,
        include_unavailable=True,
    )
    return available, all_records


def _inventory_names_set(inventory_path: str = "inventory.txt") -> set[str]:
    """Get canonical names of all currently available fragrance materials."""

    available, _ = _inventory_context(inventory_path)
    return {m.identity_name or m.name for m in available}


def _resolved_owned_profiles(owned: set[str]) -> dict[str, MaterialProfile]:
    profiles: dict[str, MaterialProfile] = {}
    for name in owned:
        profile = get_profile(name)
        if profile is not None:
            profiles[_identity_key(name, profile)] = profile
    return profiles


def _compute_dimension_coverage(
    owned: set[str], all_profiles: dict[str, MaterialProfile]
) -> dict[str, float]:
    """For each of 13 dimensions, compute coverage as max score among owned materials / 10."""
    coverage: dict[str, float] = {}
    for dim in DIMENSIONS:
        max_score = 0.0
        for name in owned:
            p = get_profile(name)
            if p and dim in p.character:
                max_score = max(max_score, p.character[dim])
        coverage[dim] = max_score / 10.0
    return coverage


def _compute_dimension_depth(
    owned: set[str], all_profiles: dict[str, MaterialProfile]
) -> dict[str, int]:
    """Count how many owned materials score ≥5 on each dimension."""
    depth: dict[str, int] = {d: 0 for d in DIMENSIONS}
    for name in owned:
        p = get_profile(name)
        if not p:
            continue
        for dim, val in p.character.items():
            if dim in depth and val >= 5.0:
                depth[dim] += 1
    return depth


def _adaptation_group_coverage(owned: set[str]) -> dict[str, int]:
    """Count how many owned materials are in each cross-adaptation group."""
    coverage: dict[str, int] = {}
    owned_keys = {
        _identity_key(name, get_profile(name))
        for name in owned
    }
    for group, members in CROSS_ADAPTATION_GROUPS.items():
        count = sum(
            1
            for member in members
            if _identity_key(member, get_profile(member)) in owned_keys
        )
        coverage[group] = count
    return coverage


def _anosmia_risk_materials(owned: set[str]) -> list[tuple[str, float]]:
    """Return (material, prevalence) for owned anosmia-prone materials."""
    risks = []
    owned_keys = {
        _identity_key(name, get_profile(name))
        for name in owned
    }
    for mat, data in GENETIC_ANOSMIA.items():
        if _identity_key(mat, get_profile(mat)) in owned_keys:
            risks.append((mat, data["prevalence"]))
    return risks


def _score_character_coverage(
    candidate: MaterialProfile,
    dim_coverage: dict[str, float],
    dim_depth: dict[str, int],
) -> tuple[float, list[str]]:
    """Score how much a candidate fills character coverage gaps.

    High score when the candidate has high values in dimensions where
    the inventory is weak (low coverage or low depth).
    """
    score = 0.0
    fills = []
    for dim in DIMENSIONS:
        cval = candidate.character.get(dim, 0.0)
        if cval < 3.0:
            continue
        # Gap factor: how weak is this dimension in current inventory?
        coverage_gap = max(0.0, 1.0 - dim_coverage.get(dim, 0.0))
        depth_penalty = max(0.0, 1.0 - dim_depth.get(dim, 0) / 5.0)
        gap_factor = 0.6 * coverage_gap + 0.4 * depth_penalty
        contribution = (cval / 10.0) * gap_factor * 100.0
        if contribution > 5.0:
            fills.append(dim)
        score += contribution
    # Normalise: max theoretical = 13 dimensions × 100 = 1300
    return min(100.0, score * (100 / 400)), fills


def _score_synergy_unlock(
    candidate_name: str, owned: set[str], graph: SynergyGraph
) -> tuple[float, list[str]]:
    """Score high-confidence declared synergies with owned materials.

    Role/fingerprint inference is intentionally excluded. The previous scorer
    counted hundreds of inferred edges and saturated virtually every candidate
    at 100, so the axis carried no ranking information.
    """

    new_edges: list[tuple[str, float]] = []
    owned_keys = {
        _identity_key(name, get_profile(name))
        for name in owned
    }
    node = graph.nodes.get(candidate_name)
    if node is None:
        return 0.0, []
    for partner, edge in node.edges.items():
        if "expert_declared" not in edge.sources or edge.weight <= 0:
            continue
        if _identity_key(partner, get_profile(partner)) in owned_keys:
            new_edges.append((partner, edge.weight * edge.confidence))
    if not new_edges:
        return 0.0, []
    new_edges.sort(key=lambda pair: pair[1], reverse=True)
    # Five strong declared links are enough to saturate this screening axis.
    score = min(100.0, sum(value for _name, value in new_edges) / 3.6 * 100.0)
    return score, [name for name, _value in new_edges[:10]]


def _score_cross_adaptation(
    candidate_name: str,
    owned: set[str],
    group_coverage: dict[str, int],
) -> tuple[float, list[str]]:
    """Score how much the candidate improves cross-adaptation diversity.

    Highest score when the candidate is in a group with ZERO owned materials
    (opens entirely new receptor territory).
    """
    {n.lower() for n in owned}
    candidate_groups = []
    for group, members in CROSS_ADAPTATION_GROUPS.items():
        if candidate_name.lower() in [m.lower() for m in members]:
            candidate_groups.append(group)

    if not candidate_groups:
        # Material not in any known group — novel territory
        # Missing annotation is unknown evidence, not proof of new receptor
        # territory. Unknowns receive no score.
        return 0.0, []

    new_groups = []
    reinforcement_score = 0.0
    for g in candidate_groups:
        count = group_coverage.get(g, 0)
        if count == 0:
            new_groups.append(g)
        elif count < 3:
            reinforcement_score += (3 - count) * 10.0

    if new_groups:
        return min(100.0, len(new_groups) * 50.0 + reinforcement_score), new_groups
    return min(100.0, reinforcement_score), []


def _score_versatility(candidate: MaterialProfile) -> float:
    """Score how many formula archetypes the candidate is useful in.

    Based on character breadth (how many dimensions ≥ 3) and role versatility.
    """
    breadth = sum(1 for v in candidate.character.values() if v >= 3.0)
    role_mult = ROLE_VERSATILITY.get(candidate.role, 1.0)
    # Also score texture diversity — materials with unique textures are more versatile
    texture_bonus = 10.0 if candidate.texture in ("bridge", "cocoon", "veil", "halo") else 0.0
    # Normalise: max breadth = 13
    return min(100.0, (breadth / 8.0) * 70.0 * role_mult + texture_bonus)


def _score_intelligence_depth(candidate_name: str, candidate: MaterialProfile) -> float:
    """Score how much data we have on this material (Hill params, character zones, ODT).

    Paradoxically, materials WITH data are MORE useful to buy because the engine
    can model them accurately. Unknown materials carry modelling risk.
    """
    score = 0.0
    # Has Hill equation parameters → accurate dose-response modelling
    if candidate_name in HILL_PARAMS:
        score += 35.0
    # Has character shift zones → overdose prevention modelling
    if candidate_name in CHARACTER_SHIFT_DATA:
        score += 25.0
    # Has ODT data → headspace contribution modelling
    odt_names_lower = {k.lower() for k in ODT_DATA}
    if candidate_name.lower() in odt_names_lower:
        score += 20.0
    # Has physical properties
    if candidate.mw and candidate.mw > 0:
        score += 5.0
    if candidate.vp and candidate.vp > 0:
        score += 5.0
    if candidate.clogp is not None:
        score += 5.0
    if candidate.odt and candidate.odt > 0:
        score += 5.0
    return min(100.0, score)


def _score_anosmia_redundancy(
    candidate: MaterialProfile,
    candidate_name: str,
    risk_materials: list[tuple[str, float]],
    all_profiles: dict[str, MaterialProfile],
) -> tuple[float, list[str]]:
    """Score how well the candidate backs up anosmia-prone materials.

    A candidate is a good backup if it has similar character to an anosmia-prone
    material BUT activates different receptors (i.e., is NOT in the same
    anosmia entry).
    """
    if not risk_materials:
        return 0.0, []

    backups = []
    total_backup_value = 0.0

    # Check if candidate is itself anosmia-prone (penalty)
    candidate_anosmic = candidate_name in GENETIC_ANOSMIA or any(
        k.lower() == candidate_name.lower() for k in GENETIC_ANOSMIA
    )
    if candidate_anosmic:
        return 0.0, []  # Don't recommend buying another anosmia-prone material as backup

    for risk_mat, prevalence in risk_materials:
        risk_profile = get_profile(risk_mat)
        if not risk_profile:
            continue
        dist = character_distance(candidate, risk_profile)
        if dist is not None and dist < 3.0:
            # Close character match = good backup
            backup_value = (1.0 - dist / 3.0) * prevalence * 100.0
            total_backup_value += backup_value
            backups.append(risk_mat)

    return min(100.0, total_backup_value), backups


def _score_structural_gap(
    candidate: MaterialProfile, candidate_name: str
) -> float:
    """Score based on whether this material fills known structural gaps.

    Checks: note distribution, role distribution, texture diversity.
    """
    score = 0.0
    # Materials with rare roles get a bonus
    if candidate.role in ("trace", "bridge"):
        score += 20.0
    # Materials with rare textures get a bonus
    if candidate.texture in ("halo", "veil", "cocoon"):
        score += 15.0
    # Character materials with strong synergy lists are more structurally useful
    if candidate.synergies and len(candidate.synergies) > 5:
        score += min(30.0, len(candidate.synergies) * 3.0)
    # Materials with known avoid list = the engine can prevent clashes
    if candidate.avoid and len(candidate.avoid) > 0:
        score += 10.0
    return min(100.0, score)


def _model_authority(name: str) -> tuple[str, float]:
    """Classify whether a candidate can be modeled quantitatively as sold."""

    low = name.casefold()
    opaque_tokens = (
        "f-tec",
        "ftec",
        "fleuressence",
        " base",
        " accord",
        " fo",
        "molecule iris",
        "reconstitution",
    )
    if any(token in low for token in opaque_tokens):
        return "OPAQUE_MIXTURE_PROXY", 0.60

    natural_tokens = (
        " absolute",
        " eo",
        " oil",
        " resinoid",
        " balsam",
        " orris butter",
    )
    if any(token in low for token in natural_tokens):
        if get_composite_metadata(name) is not None:
            return "NATURAL_LITERATURE_COMPOSITE", 1.0
        return "NATURAL_COMPOSITE_UNRESOLVED", 0.60
    return "MONOMOLECULAR_OR_DECLARED_STOCK_MODEL", 1.0


# ---------------------------------------------------------------------------
# Composite scoring
# ---------------------------------------------------------------------------

def _compute_composite(scores: dict[str, float]) -> float:
    """Weighted geometric mean of axis scores.

    Adds 1.0 to each score before log to handle zeros without collapse.
    """
    log_sum = 0.0
    weight_sum = 0.0
    for axis, weight in AXIS_WEIGHTS.items():
        val = scores.get(axis, 0.0)
        log_sum += weight * math.log(val + 1.0)
        weight_sum += weight
    if weight_sum == 0:
        return 0.0
    return math.exp(log_sum / weight_sum) - 1.0


def _assign_tier(composite: float) -> str:
    """Assign purchase priority tier based on composite score."""
    if composite >= 55:
        return "essential"
    elif composite >= 40:
        return "high_value"
    elif composite >= 25:
        return "useful"
    elif composite >= 12:
        return "niche"
    else:
        return "low_priority"


# ---------------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------------

def analyze_expansion(
    inventory_path: str = "inventory.txt",
    top_n: int = DEFAULT_TOP_N,
    exclude: Optional[set[str]] = None,
    *,
    include_replenishment: bool = False,
) -> ExpansionReport:
    """Run full expansion analysis and return ranked purchase recommendations.

    Parameters
    ----------
    inventory_path : str
        Path to inventory.txt.
    top_n : int
        Max candidates to return.
    exclude : set[str] | None
        Additional materials to exclude from recommendations.
    include_replenishment : bool
        When false (default), materials already listed as depleted or otherwise
        unavailable are not presented as range extensions.  When true, they may
        be returned with ``purchase_mode='replenishment'``.

    Returns
    -------
    ExpansionReport
        Ranked candidates with full scoring breakdown.
    """
    exclusions = EXCLUDE_MATERIALS | (exclude or set())
    exclusion_keys = {
        _identity_key(name, get_profile(name))
        for name in exclusions
    }

    # 1. Parse current inventory
    available_records, all_inventory_records = _inventory_context(inventory_path)
    owned = {item.identity_name or item.name for item in available_records}
    all_profiles = get_all_profiles()
    owned_profiles = _resolved_owned_profiles(owned)
    owned_identity_keys = set(owned_profiles)
    # Preserve even unresolved inventory labels so an unmodelled owned item is
    # never recommended back to the user under the same label.
    owned_identity_keys.update(
        _identity_key(item.identity_name or item.name, _profile_for_inventory_item(item))
        for item in available_records
    )
    # Shelf categories are not chemical roles. Include every currently owned
    # label for identity exclusion so a fixative filed under carriers is not
    # misreported as a depleted purchase opportunity.
    owned_identity_keys.update(
        _identity_key(item.identity_name or item.name, _profile_for_inventory_item(item))
        for item in all_inventory_records
        if item.status == "owned"
    )
    all_inventory_keys = {
        _identity_key(item.identity_name or item.name, _profile_for_inventory_item(item))
        for item in all_inventory_records
    }
    unavailable_only_keys = all_inventory_keys - owned_identity_keys

    # 2. Build context metrics
    dim_coverage = _compute_dimension_coverage(owned, all_profiles)
    dim_depth = _compute_dimension_depth(owned, all_profiles)
    group_coverage = _adaptation_group_coverage(owned)
    risk_materials = _anosmia_risk_materials(owned)

    weakest_dims = sorted(dim_coverage, key=lambda d: dim_coverage[d])[:5]
    missing_groups = [g for g, c in group_coverage.items() if c == 0]

    anosmia_exposure = 0.0
    if owned:
        anosmia_count = sum(
            1 for mat in GENETIC_ANOSMIA
            if _identity_key(mat, get_profile(mat)) in owned_identity_keys
        )
        anosmia_exposure = anosmia_count / len(owned)

    # 3. Build synergy graph with ALL known materials (not just owned)
    all_material_names = list(all_profiles.keys())
    graph = SynergyGraph()
    graph.build(all_material_names)

    # 4. Identify candidates: in _PROFILES but NOT in inventory
    candidates: list[ExpansionCandidate] = []
    excluded_owned_aliases: list[str] = []
    excluded_existing_unavailable: list[str] = []
    seen_candidate_keys: set[str] = set()

    for name, profile in all_profiles.items():
        if profile is None:
            continue
        if profile.role in {"solvent", "carrier"} or profile.note == "carrier":
            continue
        if name.lower().endswith(" materials"):
            # Aggregate profile used by legacy heuristics, not a purchasable SKU.
            continue

        identity_key = _identity_key(name, profile)
        if identity_key in seen_candidate_keys:
            continue
        if identity_key in owned_identity_keys:
            excluded_owned_aliases.append(name)
            continue
        if identity_key in exclusion_keys:
            continue
        if identity_key in unavailable_only_keys and not include_replenishment:
            excluded_existing_unavailable.append(name)
            continue

        seen_candidate_keys.add(identity_key)

        ec = ExpansionCandidate(
            name=name,
            profile=profile,
            identity_key=identity_key,
            purchase_mode=(
                "replenishment"
                if identity_key in unavailable_only_keys
                else "range_extension"
            ),
        )
        (
            ec.modelling_authority,
            ec.modelling_authority_multiplier,
        ) = _model_authority(name)

        if owned_profiles:
            _closest_key, closest_profile = min(
                owned_profiles.items(),
                key=lambda pair: character_distance(profile, pair[1]),
            )
            ec.closest_owned = closest_profile.name
            ec.closest_owned_distance = character_distance(profile, closest_profile)

        # Score each axis
        ec.character_coverage_score, ec.fills_dimensions = _score_character_coverage(
            profile, dim_coverage, dim_depth
        )
        ec.synergy_unlock_score, ec.new_synergies = _score_synergy_unlock(
            name, owned, graph
        )
        ec.cross_adaptation_score, ec.new_adaptation_groups = _score_cross_adaptation(
            name, owned, group_coverage
        )
        ec.versatility_score = _score_versatility(profile)
        ec.intelligence_depth_score = _score_intelligence_depth(name, profile)
        ec.anosmia_redundancy_score, ec.backs_up_anosmic = _score_anosmia_redundancy(
            profile, name, risk_materials, all_profiles
        )
        ec.structural_gap_score = _score_structural_gap(profile, name)

        # Composite
        axis_scores = {
            "character_coverage": ec.character_coverage_score,
            "synergy_unlock": ec.synergy_unlock_score,
            "cross_adaptation": ec.cross_adaptation_score,
            "versatility": ec.versatility_score,
            "intelligence_depth": ec.intelligence_depth_score,
            "anosmia_redundancy": ec.anosmia_redundancy_score,
            "structural_gap": ec.structural_gap_score,
        }
        ec.composite_score = _compute_composite(axis_scores)
        # Range extension should reward new olfactory territory, not a second
        # implementation of an already-covered profile.  This is deliberately
        # a soft functional-overlap discount: similarity never establishes
        # chemical identity or interchangeability.
        if ec.closest_owned_distance is not None:
            if ec.closest_owned_distance <= 1.0:
                ec.functional_overlap_multiplier = 0.25
            elif ec.closest_owned_distance <= 2.0:
                ec.functional_overlap_multiplier = 0.50
            elif ec.closest_owned_distance <= 3.0:
                ec.functional_overlap_multiplier = 0.75
        ec.composite_score *= (
            ec.functional_overlap_multiplier * ec.modelling_authority_multiplier
        )
        ec.tier = _assign_tier(ec.composite_score)

        # Build human-readable reasons
        reasons = []
        if ec.fills_dimensions:
            reasons.append(f"Fills weak dimensions: {', '.join(ec.fills_dimensions)}")
        if ec.new_synergies:
            reasons.append(
                f"Unlocks {len(ec.new_synergies)} synergies with: "
                f"{', '.join(ec.new_synergies[:5])}"
                + (f" +{len(ec.new_synergies)-5} more" if len(ec.new_synergies) > 5 else "")
            )
        if ec.new_adaptation_groups:
            reasons.append(
                f"Opens new receptor territory: {', '.join(ec.new_adaptation_groups)}"
            )
        if ec.backs_up_anosmic:
            reasons.append(
                f"Backs up anosmia-prone: {', '.join(ec.backs_up_anosmic)}"
            )
        if ec.intelligence_depth_score >= 50:
            reasons.append("Well-characterised in engine (Hill/ODT/character zones)")
        if ec.versatility_score >= 60:
            reasons.append(f"High versatility ({profile.role} role, {profile.note} note)")
        if ec.purchase_mode == "replenishment":
            reasons.append("Replenishment of a stock already recorded as unavailable")
        if ec.closest_owned and ec.closest_owned_distance is not None:
            reasons.append(
                f"Closest owned character profile: {ec.closest_owned} "
                f"(distance {ec.closest_owned_distance:.2f}; similarity is not identity)"
            )
        if ec.functional_overlap_multiplier < 1.0:
            reasons.append(
                "Range-extension score discounted for strong functional overlap "
                f"(x{ec.functional_overlap_multiplier:.2f})"
            )
        if ec.modelling_authority_multiplier < 1.0:
            reasons.append(
                f"Quantitative authority `{ec.modelling_authority}`; score discounted "
                f"until sold-form composition/OAV support exists "
                f"(x{ec.modelling_authority_multiplier:.2f})"
            )
        ec.reasons = reasons

        candidates.append(ec)

    # 5. Sort by composite score descending
    candidates.sort(key=lambda c: c.composite_score, reverse=True)

    # 6. Build diagnostics
    diagnostics = [
        f"Inventory: {len(owned)} available non-solvent stock entries",
        f"Candidates evaluated: {len(candidates)}",
        f"Owned aliases/stock variants excluded: {len(set(excluded_owned_aliases))}",
        f"Existing unavailable stocks excluded from range extension: {len(set(excluded_existing_unavailable))}",
        f"Weakest dimensions: {', '.join(weakest_dims)}",
        f"Missing adaptation groups: {', '.join(missing_groups) or 'none'}",
        f"Anosmia exposure: {anosmia_exposure:.1%} of inventory",
    ]

    tier_counts = {}
    for c in candidates:
        tier_counts[c.tier] = tier_counts.get(c.tier, 0) + 1
    diagnostics.append(
        f"Tier distribution: {', '.join(f'{t}: {n}' for t, n in sorted(tier_counts.items()))}"
    )

    return ExpansionReport(
        candidates=candidates[:top_n],
        inventory_size=len(owned),
        candidates_evaluated=len(candidates),
        dimension_coverage=dim_coverage,
        weakest_dimensions=weakest_dims,
        adaptation_group_coverage=group_coverage,
        missing_groups=missing_groups,
        anosmia_exposure=anosmia_exposure,
        diagnostics=diagnostics,
        excluded_owned_aliases=tuple(sorted(set(excluded_owned_aliases))),
        excluded_existing_unavailable=tuple(
            sorted(set(excluded_existing_unavailable))
        ),
    )


# ---------------------------------------------------------------------------
# CLI / report generation
# ---------------------------------------------------------------------------

def format_report(report: ExpansionReport) -> str:
    """Format ExpansionReport as readable Markdown."""
    lines = [
        "# Aromachemical Expansion Recommendations",
        "",
        f"**Authority:** `{report.ranking_authority}`",
        f"**Inventory scope:** `{report.inventory_scope}`",
        "",
        "This is a model-ranked screening list, not a purchase order. Price, supplier availability,",
        "regulatory suitability, and a bench blotter trial remain independent acceptance gates.",
        "",
        "## Inventory Analysis",
        "",
    ]

    # Dimension coverage table
    lines.append("### 13-D Character Coverage")
    lines.append("")
    lines.append("| Dimension | Coverage | Depth (≥5 materials) |")
    lines.append("|-----------|----------|---------------------|")
    for dim in sorted(report.dimension_coverage, key=lambda d: report.dimension_coverage[d]):
        cov = report.dimension_coverage[dim]
        bar = "█" * int(cov * 10) + "░" * (10 - int(cov * 10))
        lines.append(f"| {dim} | {bar} {cov:.0%} | — |")
    lines.append("")

    # Adaptation group coverage
    lines.append("### Cross-Adaptation Group Coverage")
    lines.append("")
    lines.append("| Group | Owned Materials |")
    lines.append("|-------|----------------|")
    for g in sorted(report.adaptation_group_coverage, key=lambda g: report.adaptation_group_coverage[g]):
        count = report.adaptation_group_coverage[g]
        flag = " ⚠️ EMPTY" if count == 0 else ""
        lines.append(f"| {g} | {count}{flag} |")
    lines.append("")

    # Diagnostics
    lines.append("### Diagnostics")
    lines.append("")
    for d in report.diagnostics:
        lines.append(f"- {d}")
    lines.append("")

    # Top recommendations
    lines.append("---")
    lines.append("")
    lines.append("## Top Purchase Recommendations")
    lines.append("")

    for i, c in enumerate(report.candidates, 1):
        tier_emoji = {
            "essential": "🔴",
            "high_value": "🟠",
            "useful": "🟡",
            "niche": "🔵",
            "low_priority": "⚪",
        }.get(c.tier, "⚪")

        lines.append(f"### {i}. {c.name} {tier_emoji} {c.tier.upper()}")
        lines.append("")
        lines.append(f"**Composite Score:** {c.composite_score:.1f}")
        lines.append(f"**Purchase mode:** `{c.purchase_mode}`")
        lines.append(f"**Quantitative authority:** `{c.modelling_authority}`")
        lines.append(f"**Note:** {c.profile.note} | **Role:** {c.profile.role} | **Texture:** {c.profile.texture or '—'}")
        lines.append("")

        # Axis breakdown
        lines.append("| Axis | Score |")
        lines.append("|------|-------|")
        lines.append(f"| Character Coverage | {c.character_coverage_score:.0f} |")
        lines.append(f"| Synergy Unlock | {c.synergy_unlock_score:.0f} |")
        lines.append(f"| Cross-Adaptation | {c.cross_adaptation_score:.0f} |")
        lines.append(f"| Versatility | {c.versatility_score:.0f} |")
        lines.append(f"| Intelligence Depth | {c.intelligence_depth_score:.0f} |")
        lines.append(f"| Anosmia Redundancy | {c.anosmia_redundancy_score:.0f} |")
        lines.append(f"| Structural Gap | {c.structural_gap_score:.0f} |")
        lines.append("")

        if c.reasons:
            lines.append("**Why buy this:**")
            for r in c.reasons:
                lines.append(f"- {r}")
            lines.append("")

    lines.extend(["---", "", "## Model Limitations", ""])
    for limitation in report.model_limitations:
        lines.append(f"- {limitation}")

    return "\n".join(lines)


def run_expansion_analysis(
    inventory_path: str = "inventory.txt",
    output_path: str = "expansion_recommendations.md",
    top_n: int = DEFAULT_TOP_N,
) -> ExpansionReport:
    """Run analysis and write Markdown report."""
    report = analyze_expansion(inventory_path=inventory_path, top_n=top_n)
    md = format_report(report)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md)
    return report


if __name__ == "__main__":
    report = run_expansion_analysis()
    print(f"Expansion analysis complete. {report.candidates_evaluated} candidates evaluated.")
    print("Top 5 recommendations:")
    for i, c in enumerate(report.candidates[:5], 1):
        print(f"  {i}. {c.name} — {c.composite_score:.1f} ({c.tier})")
        for r in c.reasons[:2]:
            print(f"     → {r}")
