"""Formula Optimization Recommendations Engine.

For each formula, identifies weakest scoring axes, generates targeted
ingredient-level recommendations from inventory, rescores the modified
formula, and ranks by composite improvement delta.

Recommendation types:
  ADD       — introduce a new material not currently in the formula
  INCREASE  — bump an existing underdosed material
  REBALANCE — redistribute percentages (no new material)

Intervention modes:
  pre_mix     — classic formulation-time optimization
  post_mix    — conservative add-only corrections for an already mixed bottle
  between_mix — corrective suggestions informed by observations / intent tags
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from engine.chemical_data_validator import is_blocked_chemical
from engine.dose_response import CHARACTER_SHIFT_DATA
from engine.gap_detector import GapDetector
from engine.ingredient_catalog import find_ingredient
from engine.intervention_context import (
    InterventionContext,
    ObservationProfile,
    additive_dose_ul_from_pct,
)
from engine.inventory_parser import parse_inventory
from engine.optimizer.models import (
    classify_note,
    get_theory_rules,
    material_identity_key,
    material_jellinek_quadrant_key,
    material_roudnitska_roles,
    materials_match,
)
from engine.optimizer.scoring import FormulaScorer, FormulaVector
from engine.psychophysics import CROSS_ADAPTATION_GROUPS, GENETIC_ANOSMIA

try:
    from engine.intervention_profiles import (
        get_profile as get_creative_profile,
    )
    from engine.intervention_profiles import (
        normalize_family_key,
    )
    from engine.intervention_profiles import (
        suggest_interventions as suggest_creative_interventions,
    )
except Exception:  # pragma: no cover - keep engine stable if profiles drift
    get_creative_profile = None  # type: ignore[assignment]
    normalize_family_key = None  # type: ignore[assignment]
    suggest_creative_interventions = None  # type: ignore[assignment]


# ═══════════════════════════════════════════════════════════════════════════════
# Inventory parsing
# ═══════════════════════════════════════════════════════════════════════════════

_INVENTORY_PATH = Path(__file__).resolve().parent.parent / "inventory.txt"

# Skip solvents/carriers — these aren't fragrance materials
_SKIP_CATEGORIES = {"solvents", "carriers"}
_SKIP_MATERIALS = {
    "ethanol 96%",
    "dpg",
    "ipm",
    "tec",
    "dep",
}

_INTERVENTION_MODES = {"pre_mix", "post_mix", "between_mix"}
_DEFAULT_MODE = "pre_mix"
_BASE_AXIS_COUNT = 4

_MODE_CONFIG: dict[str, dict[str, Any]] = {
    "pre_mix": {
        "axis_count": 4,
        "dose_scale": 1.0,
        "max_add_pct": None,
        "min_delta": 0.5,
        "min_composite_delta": 0.1,
        "min_identity_score": 68.0,
        "require_composite_gain": True,
        "conservative": False,
    },
    "post_mix": {
        "axis_count": 3,
        "dose_scale": 0.35,
        "max_add_pct": 1.0,
        "min_delta": 0.25,
        "min_composite_delta": 0.15,
        "min_identity_score": 84.0,
        "require_composite_gain": True,
        "conservative": True,
    },
    "between_mix": {
        "axis_count": 4,
        "dose_scale": 0.65,
        "max_add_pct": 2.0,
        "min_delta": 0.35,
        "min_composite_delta": 0.15,
        "min_identity_score": 78.0,
        "require_composite_gain": True,
        "conservative": True,
    },
}

_MODE_AXIS_HINTS: dict[str, tuple[str, ...]] = {
    "radiance": (
        "bright",
        "brightness",
        "lift",
        "lifting",
        "sparkle",
        "sparkling",
        "glow",
        "luminous",
        "radiance",
        "radiant",
        "airy",
        "open",
        "airier",
        "diffusive",
    ),
    "sillage": (
        "sillage",
        "trail",
        "trailing",
        "projection",
        "project",
        "spread",
        "bloom",
        "diffuse",
        "diffusion",
        "presence",
        "radiate",
    ),
    "longevity": (
        "lasting",
        "longevity",
        "tenacity",
        "tenacious",
        "anchor",
        "anchoring",
        "drydown",
        "dry-down",
        "fade",
        "fading",
        "stick",
        "staying",
    ),
    "balance": (
        "balance",
        "balanced",
        "smooth",
        "smoother",
        "blend",
        "blended",
        "bridge",
        "bridging",
        "round",
        "rounded",
        "polish",
        "polished",
        "integration",
    ),
    "theory": (
        "roudnitska",
        "classical",
        "classic",
        "elegant",
        "transparent",
        "skin",
        "peau",
        "depth",
        "warmth",
        "warm",
        "modernist",
    ),
    "complexity": (
        "complex",
        "complexity",
        "layer",
        "layered",
        "nuance",
        "nuanced",
        "facet",
        "facets",
        "contrast",
        "signature",
        "dimension",
    ),
    "character_balance": (
        "sweet",
        "powder",
        "powdery",
        "spice",
        "spicy",
        "green",
        "floral",
        "woody",
        "amber",
        "resin",
        "resinous",
        "fruity",
        "berry",
        "animalic",
        "smoke",
        "smoky",
    ),
    "synergy": (
        "synergy",
        "synergistic",
        "cohesion",
        "cohesive",
        "integration",
        "integrated",
        "blend",
        "bridging",
        "bridge",
    ),
    "texture": (
        "texture",
        "textural",
        "feel",
        "mouthfeel",
        "skinfeel",
        "creamy",
        "velvet",
        "velvety",
        "soft",
        "smooth",
        "dry",
        "powder",
    ),
}

_CREATIVE_DOSE_HINTS = {
    "micro": 0.35,
    "bridge": 0.9,
    "structural": 1.5,
}

_ROUDNITSKA_ROLE_LABELS = {
    "eclat": "eclat / outward radiance",
    "transparence": "transparence / airy lift",
    "peau": "peau / skin intimacy",
    "chaleur": "chaleur / warmth",
    "profondeur": "profondeur / depth",
    "noblesse": "noblesse / refinement",
}

_MODE_EXPLANATIONS = {
    "pre_mix": "formulation-time intervention while proportions are still flexible",
    "between_mix": "next-batch correction guided by observations and intent tags",
    "post_mix": "add-only bottle correction with conservative dosing",
}


def _parse_dilution_from_name(raw: str) -> tuple[str, float]:
    """Extract dilution from inventory line like 'Alpha Irone (10%)'.
    Returns (clean_name, dilution_factor)."""
    m = re.search(r"\((\d+(?:\.\d+)?)\s*%(?:\s*(?:in\s+)?(?:DPG|TEC|IPM|DEP))?\)", raw)
    if m:
        clean = re.sub(r"\s*\(\d+(?:\.\d+)?%[^)]*\)", "", raw).strip()
        return clean, float(m.group(1)) / 100.0
    return raw.strip(), 1.0


def load_inventory() -> list[dict]:
    """Parse inventory.txt → list of {name, dilution, category}."""
    records = parse_inventory(
        _INVENTORY_PATH,
        unique=True,
        include_solvents=False,
        include_unavailable=False,
    )
    return [
        {
            "name": record.name,
            "dilution": record.dilution,
            "category": record.category,
            "catalog": find_ingredient(record.name),
        }
        for record in records
        if record.name.lower() not in _SKIP_MATERIALS
        and not any(s in record.category for s in _SKIP_CATEGORIES)
        and not is_blocked_chemical(record.name)
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# Axis → material mapping — what to add when an axis is weak
# ═══════════════════════════════════════════════════════════════════════════════

# Each entry: (material_name_substring, dose_pct, rationale)
# dose_pct is the raw % to add (before dilution adjustment)
AXIS_CANDIDATES: dict[str, list[tuple[str, float, str]]] = {
    "radiance": [
        # ── Floral / Diffusive lift ──
        ("hedione", 4.0, "radiance amplifier + volume expander"),
        ("neroli eo", 1.0, "luminous floral éclat, top-note radiance"),
        ("linalool", 2.5, "clean transparent lift, radiance diffuser"),
        ("florol", 1.5, "fresh muguet-adjacent transparency, aquatic radiance"),
        ("nympheal", 1.5, "watery transparent floral, diffusive radiance bloom"),
        ("helional", 1.5, "ozonic-green heliotrope, aquatic transparent lift"),
        # ── Aldehydic sparkle ──
        ("aldehyde c12 mna", 0.8, "metallic sparkle at trace, Chanel-style éclat"),
        ("aldehyde c11", 0.8, "fatty-aldehydic sparkle, clean laundry lift (1% dil)"),
        # ── Fresh / Green lift ──
        ("cedrat fcf oil sicilian", 2.0, "sparkling citrus lift, concrete top-note radiance"),
        ("bergamot fcf oil sicilian", 2.0, "rich bergamot éclat, top-note luminosity"),
        ("allyl amyl glycolate", 1.0, "green-pineapple laundry lift at trace"),
        ("scentenal", 0.5, "metallic-green ozone, mineral transparency (1% dil)"),
    ],
    "sillage": [
        # ── Salicylate diffusion cushion ──
        ("benzyl salicylate", 4.0, "diffusion cushion + cosmetic volume fixative"),
        ("hexyl salicylate", 3.0, "lighter salicylate cushion, green-floral volume"),
        # ── Molecular diffusers ──
        ("iso e super", 5.0, "molecular cocoon, skin-scent bloom"),
        ("cashmeran", 2.0, "woody-musky bloom diffuser (20% dil → 0.4% active)"),
        ("clearwood", 2.5, "molecular woody diffuser, patchouli-adjacent bloom"),
        ("dbca", 1.5, "gardenia-rose cosmetic volume, transparent diffusion"),
        # ── Musk projection engines ──
        ("galaxolide", 3.0, "polycyclic musk projector (80% dil → 2.4% active)"),
        ("habanolide", 1.5, "macrocyclic musk sillage engine, modern clean"),
        ("tonalide", 2.0, "warm polycyclic musk volume, laundry-clean projection (10% dil)"),
        ("ambrettolide", 1.5, "elegant macrocyclic musk, natural skin bloom (10% dil)"),
        ("exaltolide", 1.5, "macrocyclic musk bloom, powdery diffusion base (10% dil)"),
    ],
    "longevity": [
        # ── Woody fixatives ──
        ("vertofix coeur", 3.0, "woody-musky bridge, amber-cedarwood fixative"),
        ("iso e super", 5.0, "abstract-cedar molecular cocoon, high tenacity"),
        ("timberol", 2.5, "dry architectural cedarwood, tenacious woody fixative"),
        ("cedramber", 2.5, "transparent woody-amber fixative, cedarwood persistence"),
        ("clearwood", 3.0, "vetiver-patchouli hybrid, molecular fixative"),
        # ── Sandalwood fixatives ──
        ("javanol", 2.5, "premium sandalwood fixative, intimate skin-scent persistence"),
        ("ebanol", 2.0, "creamy sandalwood fixative, distinct milky tenacity"),
        # ── Amber / Balsamic fixatives ──
        ("amberwood f", 2.5, "clean amber-wood fixative, transparent persistence"),
        ("ambermax", 2.0, "ambery-woody fixative, strong tenacity (10%/50% dil)"),
        ("benzoin resinoid", 2.0, "heavy balsamic fixative, resinous base (50% in DPG)"),
        ("labdanum", 1.5, "amber-leather resinous base, natural fixative"),
        ("coumarin", 2.0, "coumarinic drydown fixative, powdery base (20% dil)"),
        # ── Musk persistence ──
        ("galaxolide", 3.0, "polycyclic musk persistence engine (80% dil → 2.4% active)"),
        ("habanolide", 1.5, "macrocyclic musk tenacity, modern clean persistence"),
        ("tonalide", 2.0, "polycyclic musk tenacity, warm laundry persistence (10% dil)"),
        ("macrolide", 2.0, "macrocyclic musk body, soft powdery longevity (10% dil)"),
        # ── Neutral / Natural fixatives ──
        ("ambrox super", 3.0, "ambergris-style drydown fixative, extends persistence"),
        ("patchouli eo", 2.0, "base anchoring natural, earthy fixative"),
        ("labdanum absolute", 1.5, "balsamic resin fixative, richer drydown anchor"),
    ],
    "balance": [
        # Balance recommendations — redistribution / filling missing note categories
        # Citrus top-note options (pick based on formula character)
        ("bergamot fcf oil sicilian", 2.0, "top-note lift for base-heavy formulas"),
        ("cedrat fcf oil sicilian", 1.5, "sharp citron top-note for base-heavy mineral accords"),
        ("bergamot eo", 2.0, "juicy citrus warmth for woody-heavy formulas"),
        ("linalool", 2.0, "transparent fresh lift for dark/heavy formulas"),
        # Heart volume
        ("hedione", 3.0, "heart-note volume for top-heavy formulas"),
        # Base cushion — rotated alternatives, no workhorse defaults
        ("hexyl salicylate", 2.5, "transparent salicylate cushion for sheer accords"),
        ("vertofix coeur", 2.5, "woody-musky bridge for disjointed formulas"),
        ("clearwood", 2.5, "molecular woody base for thin/unfinished formulas"),
        ("patchouli eo", 1.5, "earthy base anchor for top-heavy formulas"),
        ("amberwood f", 2.0, "clean amber-wood cushion for skeletal formulas"),
    ],
    "theory": [
        # Roudnitska roles: éclat, peau, profondeur, chaleur, transparence
        ("neroli eo", 1.0, "fills transparence/clean Roudnitska role"),
        ("linalool", 2.0, "fills transparence/clean Roudnitska role, natural lift"),
        ("hedione", 3.0, "fills éclat/radiance Roudnitska role"),
        # ── Peau / Skin — diversified sandalwood/salicylate selection ──
        ("hexyl salicylate", 2.5, "fills peau/skin role via lighter salicylate transparency"),
        ("javanol", 2.5, "fills peau/skin role via sandalwood intimacy"),
        ("ebanol", 2.0, "fills peau/skin role via creamy sandalwood softness"),
        ("sandalore", 2.0, "fills peau/skin role via fresh sandalwood"),
        # ── Profondeur / Depth ──
        ("evernyl", 1.5, "fills profondeur/depth via chypre mossy character"),
        ("amberwood f", 2.0, "fills profondeur/depth via clean amber-wood"),
        ("kephalis", 1.0, "fills profondeur/depth via powerful woody-amber (use sparingly)"),
        # ── Chaleur / Warmth — diversified beyond Iso E Super ──
        ("cashmeran", 2.0, "fills chaleur/warmth role, soft cocoon (20% dil)"),
        ("koavone", 2.0, "fills chaleur/warmth role, warm woody support"),
        ("ambermax", 2.0, "fills chaleur/warmth role, rounded amber (10%/50% dil)"),
        # ── Volume / Projection ──
        ("romandolide", 2.0, "fills volume/projection role, clean diffusive musk"),
        ("galaxolide", 2.5, "fills volume/projection role (80% dil → 2.0% active)"),
    ],
    "complexity": [
        # ── Green / Metallic ──
        ("cyclamen aldehyde", 1.0, "metallic-green floral, structural class diversity"),
        # ── Spice dimension ──
        ("ethyl safranate", 0.8, "saffron-spice character, fills spicy dimension"),
        ("cardamom ftec", 1.5, "aromatic spice complexity (10% dil → 0.15% active)"),
        ("black pepper ftec", 1.2, "spicy-peppery facet, peppery dimension"),
        # ── Mossy / Chypre ──
        ("evernyl", 1.5, "oakmoss/chypre character, green-mossy dimension"),
        # ── Animalic / Leather ──
        ("indole", 0.5, "animalic depth at trace (10% dil → 0.05% active)"),
        ("isobutyl quinoline", 0.3, "dirty leather at trace, animalic depth (10% dil)"),
        ("birch tar rectified", 0.3, "smoky leather at trace, phenolic dimension"),
        ("styrax ftec", 1.5, "balsamic-leather smoke, smoke/amber dimension"),
        # ── Iris / Powder ──
        ("heliotropal", 1.5, "powdery iris support, fills iris dimension"),
        ("ultralia", 0.5, "ghost iris at trace, powdery transparent dimension"),
        # ── Rose / Floral ──
        ("rose oxide", 0.8, "metallic damascone rose, geranium facet (10% dil)"),
        ("dbca", 1.0, "gardenia-rose cosmetic, clean white floral dimension"),
        # ── Incense ──
        ("olibanum resinoid", 1.5, "frankincense depth, incense dimension"),
        # ── Musk class diversity ──
        ("ethylene brassylate", 1.0, "clean macrocyclic musk, powdery-retro dimension"),
        # ── Fruity character ──
        ("paradisamide", 0.5, "tropical fruit modifier, guava-cassis at trace"),
    ],
    "character_balance": [
        # ── Powder / Sweet ──
        ("coumarin", 2.0, "powdery dimension reinforcement (20% dil)"),
        ("vanillin", 1.0, "vanilla sweetness dimension (10% dil)"),
        ("alpha irone", 1.0, "iris/orris powder dimension (10% dil)"),
        # ── Spice ──
        ("eugenol", 0.5, "spicy-warm dimension at trace"),
        ("isoeugenol", 0.5, "spicy-clove warmth dimension"),
        # ── Smoke / Leather ──
        ("guaiacol", 0.3, "smoky dimension at trace"),
        ("suederal", 1.0, "suede leather dimension (10% dil)"),
        # ── Green ──
        ("parmavert", 1.0, "green violet-leaf dimension"),
        ("dynascone", 0.3, "green galbanum bomb dimension (10% dil)"),
        ("scentenal", 0.5, "metallic-green ozone dimension (1% dil)"),
        # ── Floral ──
        ("lilyreal nd", 1.5, "clean muguet cosmetic dimension"),
        ("freesia hdi", 1.0, "green-floral transparency dimension"),
        # ── Lactonic / Creamy ──
        ("gamma decalactone", 1.5, "creamy-lactonic peach dimension"),
        ("delta decalactone", 1.5, "coconut-creamy lactonic dimension"),
        # ── Woody / Suede ──
        ("vetival", 1.5, "suede-vetiver dryness dimension"),
        ("beta ionone", 1.0, "dry woody-violet dimension"),
        # ── Resinous ──
        ("labdanum absolute", 1.5, "amber-leather resinous dimension"),
        # ── Musk variety ──
        ("tonalide", 1.5, "warm/sweet musk dimension (10% dil)"),
        ("macrolide", 1.5, "soft powdery musk dimension (10% dil)"),
        ("ethylene brassylate", 1.0, "clean powder musk dimension"),
        # ── Fruity ──
        ("blackcurrant ftec", 1.0, "dark berry fruity dimension"),
    ],
    "synergy": [
        # Specialized synergy connectors — NOT universal workhorses
        # Musk + Floral / Wood bridges
        ("cashmeran", 1.5, "synergy with florals and woods, cocoon effect (20% dil)"),
        ("habanolide", 1.5, "synergy with salicylates and florals, macrocyclic bridge"),
        ("romandolide", 1.5, "synergy with woods and florals, diffusive musk bridge"),
        # Sandalwood bridges
        ("javanol", 2.0, "synergy with musks and florals, skin-effect amplifier"),
        ("ebanol", 2.0, "synergy with musks and iris, creamy sandalwood bridge"),
        # Woody connector
        ("vertofix coeur", 2.0, "synergy with ambers and musks, woody bridge"),
        ("clearwood", 2.0, "synergy with patchouli and woody base, molecular cleaner"),
        ("linalool", 2.0, "synergy with citrus and florals, transparent connector"),
        # Amber bridge
        ("amberwood f", 2.0, "synergy with woods and musks, transparent amber connector"),
        # Floral connectors
        ("dbca", 1.5, "synergy with rose/floral accords, gardenia bridge"),
        ("hexyl salicylate", 2.0, "synergy with florals and musks, transparent fixative bridge"),
    ],
    "texture": [
        # ── Salicylate cushion ──
        ("hexyl salicylate", 2.5, "sheer cushion texture, green-floral fixative"),
        ("benzyl salicylate", 3.0, "diffusion cushion texture, cosmetic skin-feel"),
        # ── Molecular cocoon ──
        ("cashmeran", 1.5, "cocoon texture layer (20% dil)"),
        ("iso e super", 4.0, "abstract-cedar cocoon texture, molecular veil"),
        # ── Sandalwood skin-effect ──
        ("ebanol", 2.0, "skin-effect texture, creamy sandalwood"),
        ("javanol", 2.5, "premium sandalwood skin-effect, intimate texture"),
        ("bacdanol", 2.0, "milky sandalwood texture, distinct from Ebanol"),
        ("sandalore", 2.5, "sandalwood-milk texture, creamy warmth"),
        # ── Musk fabric ──
        ("galaxolide", 2.5, "clean cosmetic musk texture (80% dil)"),
        ("tonalide", 1.5, "warm musk fabric texture, laundry softness (10% dil)"),
        ("macrolide", 1.5, "soft powdery musk texture, gentle roundness (10% dil)"),
        # ── Suede / Dry wood ──
        ("suederal", 1.0, "suede leather without smoke texture (10% dil)"),
        ("vetival", 1.5, "suede-vetiver dryness texture"),
        ("clearwood", 2.5, "clean patchouli-woody texture, modern dry wood"),
        # ── Iris / Powder ──
        ("orivone", 1.5, "warm orris butter texture, suede-powder"),
    ],
}


def _normalize_mode(mode: str | None) -> str:
    """Normalize an intervention mode name."""
    normalized = (mode or _DEFAULT_MODE).strip().lower()
    if normalized not in _INTERVENTION_MODES:
        return _DEFAULT_MODE
    return normalized


def _mode_config(mode: str | None) -> dict[str, Any]:
    """Return the tuning profile for an intervention mode."""
    return _MODE_CONFIG[_normalize_mode(mode)]


def _coerce_intervention_context(
    *,
    mode: str,
    observations: Mapping[str, Any] | Sequence[Any] | str | None,
    intent_tags: Sequence[str] | None,
    batch_volume_ml: float | None,
    category_hint: str | None,
    target_style: str | None,
    context: InterventionContext | None,
) -> InterventionContext:
    """Build one stable intervention context for downstream logic."""
    if context is not None:
        return context

    observation_profile = ObservationProfile.from_value(
        observations,
        intent_tags=intent_tags,
    )
    observation_tags = _iter_text_fragments(observation_profile.all_text_hints())
    if intent_tags:
        observation_tags.extend(_iter_text_fragments(intent_tags))

    return InterventionContext(
        mode=mode,
        batch_volume_ml=batch_volume_ml,
        category_hint=category_hint,
        target_style=target_style,
        observations=observation_tags,
        observation_profile=observation_profile,
    )


def _iter_text_fragments(value: Any) -> list[str]:
    """Flatten observations / intent inputs into text fragments."""
    fragments: list[str] = []
    if value is None:
        return fragments
    if isinstance(value, str):
        fragments.append(value)
        return fragments
    if isinstance(value, Mapping):
        for key in (
            "intent",
            "intent_tags",
            "tags",
            "observations",
            "notes",
            "issues",
            "targets",
            "goal",
            "goals",
            "problem",
            "problems",
            "feedback",
            "issue_tags",
            "desired_effects",
            "must_preserve",
            "must_avoid",
            "preserve",
            "avoid",
        ):
            if key in value:
                fragments.extend(_iter_text_fragments(value[key]))
        return fragments
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        for item in value:
            fragments.extend(_iter_text_fragments(item))
        return fragments
    fragments.append(str(value))
    return fragments


def _mode_axis_bias(
    observations: Mapping[str, Any] | Sequence[Any] | str | None = None,
    intent_tags: Sequence[str] | None = None,
) -> dict[str, float]:
    """Infer axis preferences from observations / intent tags."""
    fragments = _iter_text_fragments(observations)
    if intent_tags:
        fragments.extend(_iter_text_fragments(intent_tags))
    text = " ".join(fragments).lower()

    bias: dict[str, float] = {}
    for axis, keywords in _MODE_AXIS_HINTS.items():
        score = 0.0
        for keyword in keywords:
            if keyword in text:
                score += 0.4
        if score > 0:
            bias[axis] = min(score, 1.6)
    return bias


def _extract_style_hints(
    scores: dict,
    category_hint: str | None,
    target_style: str | None,
) -> tuple[str | None, str | None]:
    """Derive family/profile hints from explicit intent or score metadata."""
    family = category_hint.strip() if category_hint else None
    profile = target_style.strip() if target_style else None

    fingerprint = scores.get("_style_fingerprint", {})
    if not isinstance(fingerprint, Mapping):
        return family, profile

    if profile is None:
        primary = fingerprint.get("primary_candidate")
        if isinstance(primary, Mapping):
            value = str(primary.get("style", "")).strip()
            if value:
                profile = value
        if profile is None:
            dominant = str(fingerprint.get("dominant_style", "")).strip()
            if dominant:
                profile = dominant

    if family is None and normalize_family_key is not None:
        for bucket in ("category_candidates", "style_candidates", "candidates"):
            items = fingerprint.get(bucket, [])
            if not isinstance(items, Sequence):
                continue
            for candidate in items:
                if not isinstance(candidate, Mapping):
                    continue
                label = str(candidate.get("style", "")).strip()
                if not label:
                    continue
                normalized = normalize_family_key(label)
                if normalized:
                    family = normalized
                    break
            if family:
                break

    return family, profile


def _creative_profile_candidates(
    *,
    scores: dict,
    inventory: list[dict],
    mode: str,
    observations: Mapping[str, Any] | Sequence[Any] | str | None,
    intent_tags: Sequence[str] | None,
    category_hint: str | None,
    target_style: str | None,
) -> list[tuple[str, float, str, str | None, str | None]]:
    """Return creative-profile-guided material candidates for the current mode."""
    if suggest_creative_interventions is None:
        return []

    family_hint, profile_hint = _extract_style_hints(scores, category_hint, target_style)
    observation_fragments = _iter_text_fragments(observations)
    if intent_tags:
        observation_fragments.extend(_iter_text_fragments(intent_tags))
    if not observation_fragments and profile_hint:
        observation_fragments = [profile_hint]

    available_materials = [item["name"] for item in inventory]
    try:
        creative = suggest_creative_interventions(
            observations=observation_fragments,
            family=family_hint,
            profile=profile_hint,
            mode=mode,
            available_materials=available_materials,
            limit=8,
        )
    except Exception:
        return []

    prepared: list[tuple[str, float, str, str | None, str | None]] = []
    seen: set[str] = set()
    for rec in creative:
        materials = getattr(rec, "materials", ())
        for material in materials:
            inv_item = _material_in_inventory(material, inventory)
            if inv_item is None:
                continue
            key = material_identity_key(inv_item["name"])
            if key in seen:
                continue
            seen.add(key)
            dose_style = getattr(rec, "dose_style", "bridge")
            base_dose = _CREATIVE_DOSE_HINTS.get(str(dose_style), 0.8)
            rationale = getattr(rec, "rationale", "")
            profile_label = getattr(rec, "profile_label", None)
            family = getattr(rec, "family", None)
            creative_label = profile_label or family or "creative direction"
            prepared.append(
                (
                    inv_item["name"],
                    base_dose,
                    f"{creative_label}: {rationale}",
                    family,
                    profile_label,
                )
            )
    return prepared


def _rank_axes_for_mode(
    scores: dict,
    mode: str,
    observations: Mapping[str, Any] | Sequence[Any] | str | None = None,
    intent_tags: Sequence[str] | None = None,
) -> list[tuple[str, float]]:
    """Rank axes using the mode and any provided observation hints."""
    cfg = _mode_config(mode)
    axis_count = int(cfg["axis_count"])
    weak_axes = identify_weak_axes(scores, n=max(_BASE_AXIS_COUNT, axis_count))
    if _normalize_mode(mode) != "between_mix":
        return weak_axes[:axis_count]

    axis_bias = _mode_axis_bias(observations=observations, intent_tags=intent_tags)
    axis_pool: dict[str, float] = {axis: score for axis, score in weak_axes}
    for axis, bias in axis_bias.items():
        if axis in scores and axis not in axis_pool:
            axis_pool[axis] = scores[axis]

    ranked = sorted(
        axis_pool.items(),
        key=lambda item: (
            item[1] - axis_bias.get(item[0], 0.0),
            item[1],
        ),
    )
    return ranked[:axis_count]


def _safe_add_pct(base_dose: float, mode: str) -> float:
    """Scale and cap candidate dose by mode."""
    cfg = _mode_config(mode)
    dose = base_dose * float(cfg["dose_scale"])
    max_add_pct = cfg.get("max_add_pct")
    if isinstance(max_add_pct, (int, float)):
        dose = min(dose, float(max_add_pct))
    return dose


def _candidate_action(
    mode: str,
    axis: str,
    existing: str | None,
) -> tuple[str, float]:
    """Choose the action label and dose factor for a candidate."""
    normalized = _normalize_mode(mode)
    if normalized == "post_mix":
        return "ADD", 1.0
    if normalized == "between_mix":
        if existing and axis in {"balance", "synergy", "texture"}:
            return "REBALANCE", 0.75
        if existing:
            return "INCREASE", 0.85
        return "ADD", 1.0
    if existing:
        return "INCREASE", 0.5
    return "ADD", 1.0


def _accept_candidate(
    delta: float,
    composite_delta: float,
    identity_score: float,
    mode: str,
) -> bool:
    """Apply mode-specific acceptance thresholds."""
    cfg = _mode_config(mode)
    if delta <= 0:
        return False
    if cfg.get("require_composite_gain", True) and composite_delta <= 0:
        return False
    if delta < float(cfg["min_delta"]) and composite_delta < float(cfg["min_composite_delta"]):
        return False
    if identity_score < float(cfg["min_identity_score"]):
        return False
    return True


def _style_name_from_scores(scores: Mapping[str, Any]) -> str | None:
    """Return the best available style label from score metadata."""
    fingerprint = scores.get("_style_fingerprint", {})
    if isinstance(fingerprint, Mapping):
        primary = fingerprint.get("primary_candidate")
        if isinstance(primary, Mapping):
            style = str(primary.get("style", "")).strip()
            if style:
                return style
        dominant = str(fingerprint.get("dominant_style", "")).strip()
        if dominant:
            return dominant
    return None


def _carles_provenance(
    *,
    fv: FormulaVector,
    scores: Mapping[str, Any],
    material_name: str,
    axis: str,
) -> list[str]:
    """Explain the recommendation through Carles note-architecture logic."""
    theory = get_theory_rules().get("carles_method", {})
    note_band = classify_note(material_name)
    dist = fv.note_distribution()
    style = _style_name_from_scores(scores) or "classical"
    target_top, target_heart, target_base = FormulaScorer.BALANCE_TARGETS.get(
        style,
        FormulaScorer.BALANCE_TARGETS["classical"],
    )
    targets = {
        "top": target_top,
        "heart": target_heart,
        "base": target_base,
    }
    actual = float(dist.get(note_band, 0.0))
    target = float(targets.get(note_band, 0.0))
    role_info = theory.get("note_distribution", {}).get(note_band, {})
    role_text = str(role_info.get("role", "")).strip()

    lines = [
        f"{note_band} material; Carles treats this band as {role_text or note_band}.",
    ]
    if axis == "balance" or target > actual:
        lines.append(
            f"{note_band} band is {actual:.1f}% now versus {target:.0f}% target for the detected {style} style."
        )
    else:
        lines.append(f"Supports the {note_band} band inside the detected {style} pyramid.")
    return lines


def _roudnitska_provenance(material_name: str) -> list[str]:
    """Explain the recommendation through Roudnitska role logic."""
    roles = sorted(material_roudnitska_roles(material_name))
    if not roles:
        return [
            "no explicit canonical role in the current knowledge graph; used here as a practical structural correction"
        ]

    pretty = [_ROUDNITSKA_ROLE_LABELS.get(role, role) for role in roles]
    if len(pretty) == 1:
        return [f"carries the {pretty[0]} role"]
    return [f"carries the roles {', '.join(pretty)}"]


def _jellinek_provenance(material_name: str) -> list[str]:
    """Explain the recommendation through Jellinek's psychological map."""
    quadrant_key = material_jellinek_quadrant_key(material_name)
    if not quadrant_key:
        return [
            "no explicit quadrant mapping in the current knowledge graph; treated as a structural rather than psychological correction"
        ]

    quadrants = get_theory_rules().get("jellinek_map", {}).get("quadrants", {})
    info = quadrants.get(quadrant_key, {}) if isinstance(quadrants, Mapping) else {}
    name = str(info.get("name", quadrant_key.replace("_", " "))).strip()
    character = str(info.get("character", "")).strip()
    if character:
        return [f"maps to {name}: {character}"]
    return [f"maps to {name}"]


def _style_provenance(
    *,
    scores: Mapping[str, Any],
    intervention: InterventionContext,
    creative_family: str | None,
    creative_profile: str | None,
) -> list[str]:
    """Explain style and creative-profile support for the recommendation."""
    lines: list[str] = []
    style = _style_name_from_scores(scores)
    if style:
        lines.append(f"supports the detected {style} style fingerprint")
    if intervention.category_hint:
        lines.append(f"category hint: {intervention.category_hint}")
    if intervention.target_style:
        lines.append(f"target style: {intervention.target_style}")
    if creative_family:
        lines.append(f"creative family cue: {creative_family}")
    if creative_profile:
        lines.append(f"creative profile cue: {creative_profile}")
    return lines


def _mode_provenance(
    *,
    mode: str,
    axis: str,
    axis_score: float,
    observations: Mapping[str, Any] | Sequence[Any] | str | None,
    intent_tags: Sequence[str] | None,
) -> list[str]:
    """Explain why this axis/recommendation was considered in the current mode."""
    lines = [
        f"selected because {axis} is currently weak at {axis_score:.1f}",
        _MODE_EXPLANATIONS.get(mode, _MODE_EXPLANATIONS[_DEFAULT_MODE]),
    ]
    axis_bias = _mode_axis_bias(observations=observations, intent_tags=intent_tags)
    if axis in axis_bias:
        lines.append("free-text observations or intent tags reinforced this axis")
    return lines


def _identity_provenance(
    identity: Mapping[str, Any],
    intervention: InterventionContext,
) -> list[str]:
    """Explain how well a candidate preserves the current perfume identity."""
    score = float(identity.get("score", 0.0))
    components = identity.get("components", {})
    lines = [f"preserves baseline identity at {score:.1f}/100"]
    if isinstance(components, Mapping):
        style_alignment = components.get("style_alignment")
        target_alignment = components.get("target_alignment")
        if style_alignment is not None:
            lines.append(f"style alignment {style_alignment}/100")
        if target_alignment is not None:
            lines.append(f"target alignment {target_alignment}/100")
    for note in identity.get("drift_notes", [])[:2]:
        lines.append(str(note))
    profile = intervention.observation_profile
    if profile.must_preserve:
        lines.append(f"must preserve: {', '.join(profile.must_preserve)}")
    if profile.must_avoid:
        lines.append(f"must avoid: {', '.join(profile.must_avoid)}")
    return lines


def _build_recommendation_provenance(
    *,
    fv: FormulaVector,
    scores: Mapping[str, Any],
    intervention: InterventionContext,
    material_name: str,
    axis: str,
    axis_score: float,
    observations: Mapping[str, Any] | Sequence[Any] | str | None,
    intent_tags: Sequence[str] | None,
    creative_family: str | None,
    creative_profile: str | None,
    identity: Mapping[str, Any],
) -> dict[str, list[str]]:
    """Build structured per-recommendation provenance for downstream rendering."""
    provenance: dict[str, list[str]] = {
        "Mode": _mode_provenance(
            mode=intervention.mode,
            axis=axis,
            axis_score=axis_score,
            observations=observations,
            intent_tags=intent_tags,
        ),
        "Carles": _carles_provenance(
            fv=fv,
            scores=scores,
            material_name=material_name,
            axis=axis,
        ),
        "Roudnitska": _roudnitska_provenance(material_name),
        "Jellinek": _jellinek_provenance(material_name),
    }
    style_lines = _style_provenance(
        scores=scores,
        intervention=intervention,
        creative_family=creative_family,
        creative_profile=creative_profile,
    )
    if style_lines:
        provenance["Style"] = style_lines
    provenance["Identity"] = _identity_provenance(identity, intervention)
    return provenance


# ═══════════════════════════════════════════════════════════════════════════════
# Recommendation dataclass
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class Recommendation:
    target_axis: str
    baseline_score: float
    action: str  # ADD, INCREASE, REBALANCE
    material: str
    dose_pct: float
    rationale: str
    new_axis_score: float
    delta: float
    new_composite: float
    composite_delta: float
    mode: str = "pre_mix"
    dose_ul: int | None = None
    family: str | None = None
    profile: str | None = None
    identity_preservation: float | None = None
    identity_drift: float | None = None
    provenance: dict[str, list[str]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════
# Core engine
# ═══════════════════════════════════════════════════════════════════════════════

# Excluded keys from axis ranking
_NON_AXES = {"arithmetic_total", "geometric_total", "total", "_radar", "detected_style"}


def identify_weak_axes(scores: dict, n: int = 4) -> list[tuple[str, float]]:
    """Return the n weakest scoring axes, sorted ascending."""
    axes = [(k, v) for k, v in scores.items() if k not in _NON_AXES and isinstance(v, (int, float))]
    axes.sort(key=lambda x: x[1])
    return axes[:n]


def _material_in_formula(name: str, fv: FormulaVector) -> str | None:
    """Check if a material (by substring) is already in the formula.
    Returns the matching ingredient name or None."""
    for ing in fv.ingredient_list():
        if materials_match(name, ing):
            return ing
    return None


def _material_in_inventory(name: str, inventory: list[dict]) -> dict | None:
    """Find a material in inventory by substring match."""
    for item in inventory:
        if materials_match(name, item["name"]):
            return item
    return None


def _annotate_warnings(
    rec: "Recommendation",
    fv: FormulaVector,
    mod_ingredients: dict[str, float],
    mod_dilutions: dict[str, float],
    total_volume_ul: float = 10000.0,
) -> None:
    """Annotate a recommendation with psychophysics and dose-response warnings.

    Checks:
    1. Genetic anosmia risk — recommended material may be invisible to N% of population
    2. Character shift risk — the new dose may push material into a different character zone
    3. Cross-adaptation — recommended material may suppress perception of existing materials
    """
    mat_name = rec.material.split(" (")[0].strip()  # strip dilution suffix

    # 1. Anosmia risk
    anosmia = GENETIC_ANOSMIA.get(mat_name)
    if anosmia:
        prev = anosmia["prevalence"]
        receptor = anosmia["receptor"]
        if prev >= 0.05:
            rec.warnings.append(
                f"⚠ ANOSMIA: {int(prev * 100)}% of population has {receptor} anosmia "
                f"to {mat_name} — consider a redundancy material"
            )

    # 2. Character shift risk
    zones = CHARACTER_SHIFT_DATA.get(mat_name)
    if zones:
        dil = mod_dilutions.get(mat_name, 1.0)
        amount = mod_ingredients.get(mat_name, 0)
        active_ul = amount * dil
        conc_pct = (active_ul / total_volume_ul) * 100.0
        current_char = zones[0].character
        current_quality = zones[0].quality
        for zone in zones:
            if conc_pct <= zone.max_conc_pct:
                current_char = zone.character
                current_quality = zone.quality
                break
        else:
            current_char = zones[-1].character
            current_quality = zones[-1].quality
        if current_quality == "negative":
            rec.warnings.append(
                f"⚠ CHARACTER SHIFT: {mat_name} at {conc_pct:.3f}% enters "
                f"negative zone ({current_char}) — reduce dose"
            )
        elif current_quality == "neutral":
            rec.warnings.append(
                f"ℹ BOUNDARY: {mat_name} at {conc_pct:.3f}% is in neutral zone "
                f"({current_char}) — near character transition"
            )

    # 3. Cross-adaptation check
    existing_names = {n.lower().strip() for n in fv.ingredient_list()}
    for group_name, members in CROSS_ADAPTATION_GROUPS.items():
        if mat_name.lower() in [m.lower() for m in members]:
            conflicting = [
                m for m in members if m.lower() != mat_name.lower() and m.lower() in existing_names
            ]
            if conflicting:
                rec.warnings.append(
                    f"ℹ CROSS-ADAPT: {mat_name} shares {group_name} receptor group "
                    f"with existing {', '.join(conflicting)} — mutual suppression likely"
                )


def generate_recommendations(
    fv: FormulaVector,
    scores: dict,
    inventory: list[dict] | None = None,
    top_n: int = 5,
    *,
    mode: str = _DEFAULT_MODE,
    observations: Mapping[str, Any] | Sequence[Any] | str | None = None,
    intent_tags: Sequence[str] | None = None,
    batch_volume_ml: float | None = None,
    category_hint: str | None = None,
    target_style: str | None = None,
    context: InterventionContext | None = None,
    scorer: FormulaScorer | None = None,
) -> list[Recommendation]:
    """Generate scored optimization recommendations for a formula.

    1. Identify weakest axes
    2. Apply intervention-mode constraints and observation hints
    3. For each selected axis, try candidate materials from inventory
    4. Rescore modified formula, compute delta
    5. Rank by composite improvement, return top N
    """
    if inventory is None:
        inventory = load_inventory()

    intervention = _coerce_intervention_context(
        mode=mode,
        observations=observations,
        intent_tags=intent_tags,
        batch_volume_ml=batch_volume_ml,
        category_hint=category_hint,
        target_style=target_style,
        context=context,
    )
    normalized_mode = intervention.mode
    if scorer is None:
        scorer = FormulaScorer()
    weak_axes = _rank_axes_for_mode(
        scores,
        normalized_mode,
        observations=observations,
        intent_tags=intent_tags,
    )
    baseline_composite = scores.get("geometric_total", 0)
    baseline_signature = scorer.identity_signature(fv, scores)
    creative_candidates = _creative_profile_candidates(
        scores=scores,
        inventory=inventory,
        mode=normalized_mode,
        observations=observations,
        intent_tags=intent_tags,
        category_hint=intervention.category_hint,
        target_style=intervention.target_style,
    )

    # ── Gap-aware synergistic filler candidates ──
    # Use GapDetector to find materials that synergize with the existing palette
    _gd = GapDetector()
    _gap_fillers = _gd.suggest_synergistic_fillers(fv.ingredient_list())
    # Inject top gap fillers as candidates for weak axes
    for gf in _gap_fillers[:5]:
        inv_match = _material_in_inventory(gf["material"], inventory)
        if inv_match is not None:
            creative_candidates.append(
                (
                    gf["material"],
                    2.0,  # moderate dose
                    f"synergistic gap filler ({gf['synergy_count']} synergies: "
                    f"{', '.join(gf['synergy_partners'])})",
                    None,
                    None,
                )
            )

    # ── Map scoring axes to AXIS_CANDIDATES keys ──
    # The scorer uses 10 axes; AXIS_CANDIDATES uses a different taxonomy.
    _axis_to_candidates: dict[str, list[str]] = {
        "longevity": ["longevity"],
        "sillage": ["sillage"],
        "texture": ["texture"],
        "synergy": ["synergy"],
        "stacking_depth": ["complexity"],
        "skin_performance": ["texture"],  # skin-effect materials
        "hedonic": ["character_balance"],
        "perceptual_clarity": [],  # adding materials hurts clarity
        "luxury": [],  # usually high; no addition helps
        "safety": [],  # handled by dose-reduction below
    }

    candidates: list[Recommendation] = []
    seen_materials: set[str] = set()  # avoid duplicate recommendations

    for _wi, (axis, axis_score) in enumerate(weak_axes):
        # Resolve candidate pool through alias mapping
        _cand_keys = _axis_to_candidates.get(axis, [axis])
        axis_candidates: list[tuple] = []
        for _ck in _cand_keys:
            axis_candidates.extend(
                (mat, dose, rat, None, None) for mat, dose, rat in AXIS_CANDIDATES.get(_ck, [])
            )
        if creative_candidates:
            axis_candidates = [
                (material, dose_pct, rationale, family, profile)
                for material, dose_pct, rationale, family, profile in creative_candidates
            ] + axis_candidates

        for raw_candidate in axis_candidates:
            if len(raw_candidate) == 3:
                mat_substr, dose_pct, rationale = raw_candidate
                creative_family = None
                creative_profile = None
            else:
                mat_substr, dose_pct, rationale, creative_family, creative_profile = raw_candidate
            if is_blocked_chemical(mat_substr):
                continue
            # Skip if we already have a recommendation for this material
            inv_item = _material_in_inventory(mat_substr, inventory)
            if inv_item is None:
                continue  # Not in inventory — skip
            if is_blocked_chemical(inv_item["name"]):
                continue
            candidate_key = material_identity_key(inv_item["name"])
            if candidate_key in seen_materials:
                continue

            existing = _material_in_formula(mat_substr, fv)
            action, action_factor = _candidate_action(normalized_mode, axis, existing)
            add_pct = _safe_add_pct(dose_pct * action_factor, normalized_mode)

            # Build modified FormulaVector
            mod_ings = dict(fv.ingredients)
            mod_dils = dict(fv.dilutions)

            if existing:
                mod_ings[existing] = mod_ings.get(existing, 0) + add_pct
            else:
                mod_ings[inv_item["name"]] = add_pct
                mod_dils[inv_item["name"]] = inv_item["dilution"]

            # Renormalize to 100%
            total = sum(mod_ings.values())
            if total > 0:
                scale = sum(fv.ingredients.values()) / total
                mod_ings = {k: v * scale for k, v in mod_ings.items()}

            mod_fv = FormulaVector(ingredients=mod_ings, dilutions=mod_dils)

            # ── 3-stage pre-screening for performance ──
            # Stage 1: Fast single-axis score (avoids full 10-axis rescore)
            new_axis_score = scorer.score_axis(mod_fv, axis)
            delta = new_axis_score - axis_score
            if delta <= 0:
                continue
            # Stage 2: Full rescore (only if axis improved)
            new_scores = scorer.score(mod_fv)
            # Re-read axis score from full rescore (may differ slightly)
            new_axis_score = new_scores.get(axis, new_axis_score)
            delta = new_axis_score - axis_score
            new_composite = new_scores.get("geometric_total", 0)
            composite_delta = new_composite - baseline_composite

            _cfg_sc = _mode_config(normalized_mode)
            if delta <= 0:
                continue
            if _cfg_sc.get("require_composite_gain", True) and composite_delta <= 0:
                continue

            # Stage 3: Identity preservation (most expensive, only for survivors)
            identity = scorer.identity_preservation(
                baseline_signature,
                new_scores,
                candidate_fv=mod_fv,
                target_style=intervention.target_style,
                category_hint=intervention.category_hint,
                must_preserve=intervention.observation_profile.must_preserve,
                must_avoid=intervention.observation_profile.must_avoid,
            )
            identity_score = float(identity.get("score", 0.0))

            if not _accept_candidate(delta, composite_delta, identity_score, normalized_mode):
                continue

            seen_materials.add(candidate_key)

            mat_display = inv_item["name"]
            if inv_item["dilution"] < 1.0:
                mat_display += f" ({int(inv_item['dilution'] * 100)}%)"

            candidates.append(
                Recommendation(
                    target_axis=axis,
                    baseline_score=axis_score,
                    action=action,
                    material=mat_display,
                    dose_pct=round(add_pct, 1),
                    rationale=rationale,
                    new_axis_score=round(new_axis_score, 1),
                    delta=round(delta, 1),
                    new_composite=round(new_composite, 1),
                    composite_delta=round(composite_delta, 1),
                    mode=normalized_mode,
                    dose_ul=(
                        additive_dose_ul_from_pct(add_pct, intervention.batch_volume_ml)
                        if normalized_mode == "post_mix"
                        else None
                    ),
                    family=creative_family,
                    profile=creative_profile,
                    identity_preservation=round(identity_score, 1),
                    identity_drift=round(max(0.0, 100.0 - identity_score), 1),
                    provenance=_build_recommendation_provenance(
                        fv=fv,
                        scores=scores,
                        intervention=intervention,
                        material_name=inv_item["name"],
                        axis=axis,
                        axis_score=axis_score,
                        observations=observations,
                        intent_tags=intent_tags,
                        creative_family=creative_family,
                        creative_profile=creative_profile,
                        identity=identity,
                    ),
                )
            )
            # Annotate with psychophysics / dose-response warnings
            _annotate_warnings(
                candidates[-1],
                fv,
                mod_ings,
                mod_dils,
                total_volume_ul=sum(fv.ingredients.values()) * 100,
            )

    # Sort by identity preservation first, then technical gain.
    candidates.sort(
        key=lambda r: (
            r.identity_preservation or 0.0,
            r.composite_delta,
            r.delta,
        ),
        reverse=True,
    )
    return candidates[:top_n]


def generate_intervention_recommendations(
    fv: FormulaVector,
    scores: dict,
    inventory: list[dict] | None = None,
    top_n: int = 5,
    *,
    mode: str = _DEFAULT_MODE,
    observations: Mapping[str, Any] | Sequence[Any] | str | None = None,
    intent_tags: Sequence[str] | None = None,
    batch_volume_ml: float | None = None,
    category_hint: str | None = None,
    target_style: str | None = None,
    context: InterventionContext | None = None,
) -> list[Recommendation]:
    """Mode-aware wrapper for recommendation generation."""
    return generate_recommendations(
        fv,
        scores,
        inventory=inventory,
        top_n=top_n,
        mode=mode,
        observations=observations,
        intent_tags=intent_tags,
        batch_volume_ml=batch_volume_ml,
        category_hint=category_hint,
        target_style=target_style,
        context=context,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Formatting
# ═══════════════════════════════════════════════════════════════════════════════


def _stars_for_delta(composite_delta: float) -> str:
    """Convert composite delta to a 1-5 star impact rating."""
    if composite_delta >= 3.0:
        return "★★★★★"
    if composite_delta >= 2.0:
        return "★★★★☆"
    if composite_delta >= 1.0:
        return "★★★☆☆"
    if composite_delta >= 0.5:
        return "★★☆☆☆"
    return "★☆☆☆☆"


def format_recommendations(
    formula_name: str,
    recs: list[Recommendation],
    scores: dict,
    *,
    mode: str = _DEFAULT_MODE,
) -> str:
    """Format recommendations as a text block for the detailed report."""
    normalized_mode = _normalize_mode(mode)
    lines = []
    lines.append("")
    title = "  ◆ OPTIMIZATION RECOMMENDATIONS"
    if normalized_mode != _DEFAULT_MODE:
        title += f" [{normalized_mode.replace('_', '-').upper()}]"
    lines.append(title)
    lines.append("  " + "─" * 100)

    if not recs:
        lines.append("    No high-impact optimizations identified — formula is well-balanced.")
        return "\n".join(lines)

    # Header
    lines.append(
        f"    {'Target Axis':<18s} {'Action':<9s} {'Material':<30s} "
        f"{'Dose%':>5s}  {'Δ Axis':>7s}  {'Δ Total':>7s}  {'Impact':<9s} Rationale"
    )
    lines.append("  " + "─" * 100)

    for r in recs:
        axis_display = f"{r.target_axis}({r.baseline_score:.0f})"
        delta_display = f"+{r.delta:.1f}" if r.delta >= 0 else f"{r.delta:.1f}"
        comp_display = (
            f"+{r.composite_delta:.1f}" if r.composite_delta >= 0 else f"{r.composite_delta:.1f}"
        )
        stars = _stars_for_delta(r.composite_delta)
        rationale = r.rationale
        if normalized_mode == "post_mix" and r.dose_ul is not None:
            rationale = f"{rationale} (~{r.dose_ul} uL / bottle)"
        lines.append(
            f"    {axis_display:<18s} {r.action:<9s} {r.material:<30s} "
            f"{r.dose_pct:5.1f}  {delta_display:>7s}  {comp_display:>7s}  {stars:<9s} {rationale}"
        )
        for label, details in (r.provenance or {}).items():
            normalized_details = [str(detail).strip() for detail in details if str(detail).strip()]
            if not normalized_details:
                continue
            if len(normalized_details) == 1:
                lines.append(f"      ↳ {label}: {normalized_details[0]}")
                continue
            lines.append(f"      ↳ {label}:")
            for detail in normalized_details:
                lines.append(f"        - {detail}")

    lines.append("")
    return "\n".join(lines)


def find_hidden_fixatives(vp_threshold: float = 1.0) -> list[dict]:
    """Scan ALL ingredient_intelligence _PROFILES for materials whose VP classifies
    them as fixatives (< vp_threshold Pa) but whose note/role places them in
    top/heart categories — the classic blind spot when optimizing for longevity.

    A 'hidden fixative' is any material whose vapor pressure is low enough to
    persist well into the drydown but whose perfumery category (citrus, floral,
    fruity, green, etc.) makes it easy to overlook when reaching for 'base'
    or 'musk' materials.

    Returns a list of dicts sorted by VP ascending (best fixatives first):
        { "name": str, "vp": float, "note": str, "role": str,
          "category": str, "families": list[str], "why": str }
    """
    from engine.ingredient_intelligence import _PROFILES

    results: list[dict] = []
    for mat_name, profile in _PROFILES.items():
        vp = profile.get("vp", None)
        if vp is None or vp > vp_threshold:
            continue
        note = profile.get("note", "unknown")
        role = profile.get("role", "unknown")
        char = profile.get("character", {})
        # Determine dominant odor family from character keys
        families = sorted(char, key=char.get, reverse=True)[:3] if char else []
        why_parts = []
        if note in ("top", "heart"):
            why_parts.append(f"note={note} (not base)")
        if vp < 0.01:
            why_parts.append(f"VP={vp:.4f}Pa — below 0.01 threshold")
        else:
            why_parts.append(f"VP={vp:.4f}Pa")
        results.append(
            {
                "name": mat_name,
                "vp": vp,
                "note": note,
                "role": role,
                "families": families,
                "why": "; ".join(why_parts),
            }
        )
    results.sort(key=lambda r: r["vp"])
    return results
